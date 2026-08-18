import os
import re
import math
import subprocess
import logging
import tiktoken
import json
import aiohttp
import random
import hashlib
import functools
from pathlib import Path

import yaml
import asyncio
import OpenGL.GL as gl
import live2d.v3 as live2d
from collections import deque

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, QTimerEvent, QPropertyAnimation, QEasingCurve, pyqtProperty, QTimer, QRect, QSize
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtGui import QPixmap, QFont, QPainter, QColor, QCursor, QPainterPath, QLinearGradient, QPalette, QIcon
from PyQt6.QtWidgets import (QApplication, QLabel, QMessageBox, QPushButton, QWidget, QHBoxLayout, QDialog, QVBoxLayout,
    QGraphicsDropShadowEffect, QFrame, QScrollArea, QGridLayout, QGraphicsOpacityEffect, QLineEdit, QTextEdit, QComboBox,
    QSpinBox, QFileDialog, QInputDialog, QPlainTextEdit, QStackedWidget, QListWidget, QListWidgetItem, QMenu)

from app.utils.ai_clients.prompt_engine import PromptEngine
from app.utils.ai_clients.ai_factory import AIFactory
from app.utils.backend_updater import LlamaUpdater
from app.configuration import configuration

logger = logging.getLogger("Interface Signals")

def safe_paint(method):
    @functools.wraps(method)
    def wrapper(self, event):
        try:
            return method(self, event)
        except Exception:
            logger.exception(f"paintEvent failed in {type(self).__name__}")
    return wrapper

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

class Live2DWidget(QOpenGLWidget):
    """
    Initializes the Live2DWidget for rendering Live2D models.
    """
    def __init__(self, parent=None, model_path=None, character_name=None):
        super().__init__(parent)

        if model_path is None:
            logger.error("model_path must be provided")

        self.configuration_characters = configuration.ConfigurationCharacters()
        self.configuration_settings = configuration.ConfigurationSettings()

        self.model_path = model_path
        self.character_name = character_name

        self.output_device = self.configuration_settings.get_main_setting("output_device_real_index")

        logger.info("Initializing Live2D...")
        live2d.init()
        logger.info("Live2D initialized.")

        self.live2d_model = None
        self.live2d_model_loaded = False
        self.opengl_initialized = False
        self.timerId = None

        self.dragging = False
        self.right_button_pressed = False
        self.dx = 0.0
        self.dy = 0.0
        self.last_mouse_x = 0.0
        self.last_mouse_y = 0.0
        self.scale = 1.0
        self.min_scale = 0.5
        self.max_scale = 2.0
        self.drag_sensitivity = 0.5

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop, True)
        self.setAutoFillBackground(False)
        self.setStyleSheet("background: transparent;")
        logger.info("Widget initialized.")
        
    def initializeGL(self) -> None:
        """
        Initializes OpenGL and loads the Live2D model.
        """
        if self.opengl_initialized:
            logger.info("OpenGL already initialized, skipping initialization.")
            return
        
        logger.info("Initializing OpenGL...")
        try:
            self.makeCurrent()
            logger.info("Current OpenGL context activated.")
        except Exception as e:
            logger.info(f"Error activating OpenGL context: {e}")
            return
        
        if live2d.LIVE2D_VERSION == 3:
            logger.info("Initializing GLEW...")
            try:
                live2d.glInit()
                logger.info("GLEW successfully initialized.")
            except Exception as e:
                logger.info(f"Error initializing GLEW: {e}")
                return
        
        logger.info("OpenGL initialized.")
        self.opengl_initialized = True

        if not self.live2d_model_loaded:
            logger.info(f"Loading model from {self.model_path}...")
            try:
                self.live2d_model = live2d.LAppModel()
                self.live2d_model.SetAutoBreathEnable(True)
                self.live2d_model.SetAutoBlinkEnable(True)
                self.live2d_model.LoadModelJson(self.model_path)
                self.live2d_model_loaded = True
                logger.info("Model successfully loaded.")
            except Exception as e:
                logger.info(f"Error loading model: {e}")
                return

            logger.info("Starting the cycle...")
            try:
                model_fps = self.configuration_settings.get_main_setting("model_fps")
                if model_fps == 0:
                    self.timerId = self.startTimer(int(1000 / 30))
                    logger.info("30 FPS MODE")
                elif model_fps == 1:
                    self.timerId = self.startTimer(int(1000 / 60))
                    logger.info("60 FPS MODE")
                elif model_fps == 2:
                    self.timerId = self.startTimer(int(1000 / 120))
                    logger.info("120 FPS MODE")
                logger.info("Timer started.")
            except Exception as e:
                logger.error(f"Error starting timer: {e}")
                return

    def resizeGL(self, w: int, h: int) -> None:
        """
        Handles resizing of the OpenGL viewport.

        Args:
            w (int): New width of the widget.
            h (int): New height of the widget.
        """
        if self.live2d_model:
            try:
                self.live2d_model.Resize(w, h)
            except Exception as e:
                logger.error(f"Error resizing model: {e}")

    def paintGL(self) -> None:
        """
        Renders the Live2D model.
        """
        gl.glClearColor(0.0, 0.0, 0.0, 0.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glClearDepth(1.0)
        
        if self.live2d_model:
            self.live2d_model.Resize(self.width(), self.height())
            
            self.live2d_model.Update()
            self.live2d_model.Draw()

    def timerEvent(self, a0: QTimerEvent | None) -> None:
        """
        Updates the Live2D model and triggers a repaint.
        """
        self.update_live2d_emotion()
        self.update()

    def update_live2d_emotion(self):
        """
        Updates the emotion of the Live2D model based on the current character's emotion.
        """
        if not self.live2d_model:
            return

        try:
            configuration_data = self.configuration_characters.load_configuration()
            character_info = configuration_data["character_list"][self.character_name]
            conversation_method = character_info["conversation_method"]
            
            current_chat = character_info["current_chat"]
            current_emotion = character_info.get("chats", {}).get(current_chat, {}).get("current_emotion", "neutral")

            if current_emotion != getattr(self, '_last_emotion_applied', None):
                self._last_emotion_applied = current_emotion
                self.live2d_model.SetExpression(current_emotion)
                
        except Exception as e:
            logger.debug(f"update_live2d_emotion error: {e}")

    def cleanup(self):
        """
        Cleans up resources used by the Live2D model and OpenGL context.
        """
        logger.info("Releasing model resources...")
        
        if self.timerId is not None:
            logger.info("Stopping timer...")
            self.killTimer(self.timerId)
            self.timerId = None

        if self.live2d_model:
            logger.info("Releasing Live2D model...")
            try:
                live2d.dispose()
            except Exception as e:
                logger.error(f"Error releasing Live2D: {e}")
            self.live2d_model = None

        if self.opengl_initialized:
            logger.info("Deactivating OpenGL context...")
            try:
                self.doneCurrent()
            except Exception as e:
                logger.error(f"Error deactivating OpenGL context: {e}")

        self.live2d_model_loaded = False
        self.opengl_initialized = False
        logger.info("All resources released.")

    def hideEvent(self, event):
        """
        Handles the hide event by stopping the timer and cleaning up resources.
        """
        logger.info("Widget hidden, stopping timer and releasing resources.")
        if self.timerId is not None:
            self.killTimer(self.timerId)
            self.timerId = None
        
        self.cleanup()
        super().hideEvent(event)

    def closeEvent(self, event):
        """
        Handles the close event by cleaning up resources.
        """
        logger.info("Closing widget...")
        self.cleanup()
        super().closeEvent(event)

    def get_available_motions(self) -> dict[str, int]:
        try:
            if not self.model_path or not os.path.exists(self.model_path):
                return {}
            with open(self.model_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            motions_dict = data.get("FileReferences", {}).get("Motions", {})
            
            result = {}
            for group_name, motion_list in motions_dict.items():
                if isinstance(motion_list, list):
                    result[group_name] = len(motion_list)
                else:
                    result[group_name] = 1
            return result
        except Exception as e:
            logger.debug(f"Failed to parse motion groups from JSON: {e}")
            return {}

    def start_motion(self, group_name: str, no: int = 0, priority: int = 3):
        if not self.live2d_model:
            return False
        try:
            p = getattr(live2d, "MotionPriority", None)
            priority_val = getattr(p, "FORCE", 3) if priority == 3 else priority
            self.live2d_model.StartMotion(group_name, no, priority_val)
            logger.info(f"[Live2D] Playing motion: {group_name}_{no} (priority={priority_val})")
            return True
        except Exception as e:
            logger.debug(f"[Live2D] Failed to play motion {group_name}_{no}: {e}")
            return False

    def play_motion_safely(self, target_group: str):
        if not self.live2d_model:
            return
        available = self.get_available_motions()
        if not available:
            try:
                self.live2d_model.StartRandomMotion(priority=3)
            except Exception:
                pass
            return
        
        matched_group = None
        for g in available.keys():
            if g.lower() == target_group.lower():
                matched_group = g
                break
        
        if matched_group:
            max_index = available[matched_group]
            random_index = random.randint(0, max_index - 1) if max_index > 1 else 0
            self.start_motion(matched_group, random_index, 3)
        else:

            fallback_groups = ["Idle", "idle", "TapBody", "motion", "Motion"]
            for f_g in fallback_groups:
                for avail_g in available.keys():
                    if avail_g.lower() == f_g.lower():
                        max_index = available[avail_g]
                        random_index = random.randint(0, max_index - 1) if max_index > 1 else 0
                        self.start_motion(avail_g, random_index, 3)
                        return

            random_g = random.choice(list(available.keys()))
            max_index = available[random_g]
            random_index = random.randint(0, max_index - 1) if max_index > 1 else 0
            self.start_motion(random_g, random_index, 3)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        new_width = self.width()
        new_height = self.height()
        self.resize(new_width, new_height)
    
    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.last_mouse_x = event.position().x()
            self.last_mouse_y = event.position().y()
        
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_button_pressed = True
            self.last_mouse_x = event.position().x()
            self.last_mouse_y = event.position().y()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_button_pressed = False

    def mouseMoveEvent(self, event):
        x = event.position().x()
        y = event.position().y()

        if self.live2d_model and self.right_button_pressed:
            norm_x = (x / self.width()) * 2 - 1
            norm_y = (y / self.height()) * 2 - 1

            angle_x = norm_x * 30
            angle_y = norm_y * 30

            eye_x = norm_x * 1.0
            eye_y = norm_y * 1.0

            self.live2d_model.SetParameterValue("ParamAngleX", angle_x)
            self.live2d_model.SetParameterValue("ParamAngleY", -angle_y)
            self.live2d_model.SetParameterValue("ParamEyeBallX", eye_x)
            self.live2d_model.SetParameterValue("ParamEyeBallY", -eye_y)

        if self.dragging:
            dx_mouse = x - self.last_mouse_x
            dy_mouse = y - self.last_mouse_y

            scale_x = 2.0 / self.width()
            scale_y = 2.0 / self.height()
            scale_xy = min(scale_x, scale_y)

            self.dx += dx_mouse * scale_xy * self.drag_sensitivity
            self.dy -= dy_mouse * scale_xy * self.drag_sensitivity

            self.live2d_model.SetOffset(self.dx, self.dy)

            self.last_mouse_x = x
            self.last_mouse_y = y

        self.update()

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        delta = event.angleDelta().y()
        scale_step = 0.1 if delta > 0 else -0.1
        new_scale = self.scale + scale_step

        new_scale = max(self.min_scale, min(self.max_scale, new_scale))

        self.scale = new_scale
        if self.live2d_model:
            self.live2d_model.SetScale(self.scale)
        
        self.update()

class TextEditUserMessage(QtWidgets.QTextEdit):
    handle_enter_key = QtCore.pyqtSignal()
    
    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
            if event.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.handle_enter_key.emit()
                event.accept()
        else:
            super().keyPressEvent(event)

class CharacterCardCharactersGateway(QtWidgets.QFrame):
    def __init__(self, conversation_method, character_author, character_name, character_avatar, character_title, character_description, character_personality, scenario, first_message, example_messages, alternate_greetings, method, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 270)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

        self.conversation_method = conversation_method
        self.character_name = character_name
        self.character_avatar = character_avatar
        self.character_title = character_title
        self.character_description = character_description
        self.character_personality = character_personality
        self.character_scenario = scenario
        self.first_message = first_message
        self.example_messages = example_messages
        self.alternate_greetings = alternate_greetings

        self.check_character_information = method

        self.downloads = None
        self.likes = None
        self.total_tokens = None
        self.character_author = character_author

        self.pixmap = QtGui.QPixmap(character_avatar)
        if self.pixmap.isNull():
            self.pixmap = QtGui.QPixmap("app/gui/icons/logotype.png")

        self.shadow_effect = QtWidgets.QGraphicsDropShadowEffect(self)
        self.shadow_effect.setBlurRadius(15)
        self.shadow_effect.setColor(QtGui.QColor(0, 0, 0, 100))
        self.shadow_effect.setOffset(0, 5)
        self.setGraphicsEffect(self.shadow_effect)

        self._hover_scale = 1.0
        self.anim_scale = QtCore.QPropertyAnimation(self, b"hover_scale")
        self.anim_scale.setDuration(350)
        self.anim_scale.setEasingCurve(QtCore.QEasingCurve.Type.InOutCubic)

        self._darkness_alpha = 100.0
        self.anim_dark = QtCore.QPropertyAnimation(self, b"darkness_alpha")
        self.anim_dark.setDuration(350)
        self.anim_dark.setEasingCurve(QtCore.QEasingCurve.Type.InOutCubic)

        self._info_alpha = 255.0
        self.anim_info = QtCore.QPropertyAnimation(self, b"info_alpha")
        self.anim_info.setDuration(300)
        self.anim_info.setEasingCurve(QtCore.QEasingCurve.Type.InOutCubic)
        
        self.action_panel = QtWidgets.QFrame(self)
        self.action_panel.setStyleSheet("background-color: rgba(20, 20, 22, 0.9); border-radius: 20px;")
        self.action_panel.setGeometry(10, 280, 180, 40)
        self.action_panel_layout = QtWidgets.QHBoxLayout(self.action_panel)
        self.action_panel_layout.setContentsMargins(4, 4, 4, 4)
        self.action_panel_layout.setSpacing(4)
        
        self.panel_anim = QtCore.QPropertyAnimation(self.action_panel, b"pos")
        self.panel_anim.setDuration(350)
        self.panel_anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)

    @QtCore.pyqtProperty(float)
    def hover_scale(self):
        return self._hover_scale

    @hover_scale.setter
    def hover_scale(self, value):
        self._hover_scale = value
        self.update()

    @QtCore.pyqtProperty(float)
    def darkness_alpha(self):
        return self._darkness_alpha

    @darkness_alpha.setter
    def darkness_alpha(self, value):
        self._darkness_alpha = value
        self.update()

    @QtCore.pyqtProperty(float)
    def info_alpha(self):
        return self._info_alpha

    @info_alpha.setter
    def info_alpha(self, value):
        self._info_alpha = value
        self.update()

    def enterEvent(self, event):
        self.anim_scale.setEndValue(1.05)
        self.anim_dark.setEndValue(0.0)
        self.anim_info.setEndValue(0.0)
        self.panel_anim.setEndValue(QtCore.QPoint(10, 220))
        
        self.anim_scale.start()
        self.anim_dark.start()
        self.anim_info.start()
        self.panel_anim.start()
        
        self.shadow_effect.setOffset(0, 8)
        self.shadow_effect.setBlurRadius(25)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim_scale.setEndValue(1.0)
        self.anim_dark.setEndValue(100.0)
        self.anim_info.setEndValue(255.0)
        self.panel_anim.setEndValue(QtCore.QPoint(10, 280))
        
        self.anim_scale.start()
        self.anim_dark.start()
        self.anim_info.start()
        self.panel_anim.start()
        
        self.shadow_effect.setOffset(0, 5)
        self.shadow_effect.setBlurRadius(15)
        super().leaveEvent(event)

    @safe_paint
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)

        rect = self.rect()
        
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(rect), 15, 15)
        painter.setClipPath(path)

        painter.save()
        scale_factor = max(rect.width() / self.pixmap.width(), rect.height() / self.pixmap.height())
        final_scale = scale_factor * self._hover_scale
        painter.translate(rect.center())
        painter.scale(final_scale, final_scale)
        painter.drawPixmap(-self.pixmap.width() // 2, -self.pixmap.height() // 2, self.pixmap)
        painter.restore()

        if self._darkness_alpha > 0:
            painter.fillRect(rect, QtGui.QColor(0, 0, 0, int(self._darkness_alpha)))

        if self._info_alpha > 0:
            gradient = QtGui.QLinearGradient(0, rect.height() * 0.4, 0, rect.height())
            gradient.setColorAt(0, QtGui.QColor(0, 0, 0, 0))
            gradient.setColorAt(1, QtGui.QColor(0, 0, 0, int(min(220, self._info_alpha))))
            painter.fillRect(rect, QtGui.QBrush(gradient))

            painter.setPen(QtGui.QColor(255, 255, 255, int(self._info_alpha)))
            font = QtGui.QFont("Inter Tight SemiBold", 13, QtGui.QFont.Weight.Bold)
            painter.setFont(font)
            
            text_rect = QtCore.QRect(15, rect.height() - 85, rect.width() - 30, 45)
            painter.drawText(
                text_rect, 
                QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignBottom | QtCore.Qt.TextFlag.TextWordWrap, 
                self.character_name
            )

            stats_y = rect.height() - 20
            stats_x = 15
            painter.setFont(QtGui.QFont("Inter Tight SemiBold", 9))
            
            if hasattr(self, 'likes') and self.likes is not None:
                painter.setPen(QtGui.QColor(230, 41, 41, int(self._info_alpha)))
                lk_text = f"\u2764 {self.likes}"
                painter.drawText(stats_x, stats_y, lk_text)
                stats_x += painter.fontMetrics().horizontalAdvance(lk_text) + 10

            if hasattr(self, 'downloads') and self.downloads is not None:
                painter.setPen(QtGui.QColor(104, 128, 186, int(self._info_alpha)))
                dl_text = f"\ud83d\udcbe {self.downloads}"
                painter.drawText(stats_x, stats_y, dl_text)
                stats_x += painter.fontMetrics().horizontalAdvance(dl_text) + 10

            if hasattr(self, 'total_tokens') and self.total_tokens is not None:
                painter.setPen(QtGui.QColor(104, 128, 186, int(self._info_alpha)))
                tk_text = f"\u2699 {self.total_tokens}"
                painter.drawText(stats_x, stats_y, tk_text)
            
            if self.character_author:
                painter.setPen(QtGui.QColor(104, 128, 186, int(self._info_alpha)))
                dl_text = f"✒️ {self.character_author}"
                painter.drawText(stats_x, stats_y, dl_text)
                stats_x += painter.fontMetrics().horizontalAdvance(dl_text) + 10

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.check_character_information(
                self.conversation_method, self.character_name, 
                self.character_avatar, self.character_title, 
                self.character_description, self.character_personality, 
                self.character_scenario, self.first_message, self.example_messages,
                self.alternate_greetings
            )
        super().mousePressEvent(event)

def _mk_font(size: int, weight: QtGui.QFont.Weight) -> QtGui.QFont:
    f = QtGui.QFont("Inter Tight", size, weight)
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    return f

def _make_separator(accent_rgba: str) -> QFrame:
    sep = QFrame()
    sep.setFixedHeight(1)
    sep.setStyleSheet(f"background: {accent_rgba}; border: none;")
    return sep

def _fit_font_to_label(label: QLabel, text: str, max_width: int, max_height: int, base_size: int, weight: QtGui.QFont.Weight) -> None:
    size = base_size
    
    doc = QtGui.QTextDocument()
    doc.setDocumentMargin(0)
    doc.setTextWidth(max_width)
    
    while size > 7:
        font = _mk_font(size, weight)
        doc.setDefaultFont(font)
        doc.setPlainText(text)
        
        if doc.size().height() <= max_height:
            break
        size -= 1
        
    final_font = _mk_font(size, weight)
    label.setFont(final_font)
    label.setMaximumHeight(max_height)

class LorebookGatewayCard(QFrame):
    """
    Gateway card for lorebook entries.
    """
    _NORMAL = dict(
        bg0="rgba(42, 35, 26, 0.52)",
        bg1="rgba(18, 14, 10, 0.72)",
        border="rgba(255, 176, 32, 0.14)",
    )
    _HOVER = dict(
        bg0="rgba(60, 48, 32, 0.68)",
        bg1="rgba(27, 20, 12, 0.88)",
        border="rgba(255, 176, 32, 0.50)",
    )
 
    def __init__(
        self,
        title: str,
        author: str,
        description: str,
        entry_count: int,
        download_url: str,
        import_method,
        translations: dict,
        parent=None,
    ):
        super().__init__(parent)
        self.title = title
        self.author = author
        self.description = description
        self.entry_count = entry_count
        self.download_url = download_url
        self.import_method = import_method
        self.translations = translations

        self.setFixedSize(230, 298)
        self.setObjectName("LorebookCard")
        self._apply_style(False)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(255, 176, 32, 28))
        shadow.setOffset(0, 5)
        self.setGraphicsEffect(shadow)

        W = QtGui.QFont.Weight
        f_title  = _mk_font(11, W.Bold)
        f_author = _mk_font(7,  W.Medium)
        f_desc   = _mk_font(8,  W.Normal)
        f_badge  = _mk_font(8,  W.Bold)
        f_btn    = _mk_font(9,  W.Bold)

        root = QVBoxLayout(self)
        root.setContentsMargins(15, 14, 15, 13)
        root.setSpacing(0)

        hdr = QHBoxLayout()
        hdr.setSpacing(10)
        hdr.setContentsMargins(0, 0, 0, 0)

        icon_lbl = QLabel()
        pix = QPixmap("app/gui/icons/lorebook.png")
        if not pix.isNull():
            icon_lbl.setPixmap(
                pix.scaled(28, 28,
                           Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
            )
        icon_lbl.setFixedSize(28, 28)
        icon_lbl.setStyleSheet("background: transparent; border: none;")

        meta = QVBoxLayout()
        meta.setSpacing(2)
        meta.setContentsMargins(0, 0, 0, 0)

        title_lbl = QLabel(title)
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet(
            "color: rgba(255,255,255,0.95); background: transparent; border: none;"
        )
        
        fm_t = QtGui.QFontMetrics(_mk_font(11, W.Bold))
        max_title_height = fm_t.height() * 2 + 2
        
        _fit_font_to_label(title_lbl, title, 135, max_title_height, 11, W.Bold)

        author_tpl = self.translations.get("gw_card_author_prefix", "by {author}")
        author_lbl = QLabel(author_tpl.format(author=author))
        author_lbl.setFont(f_author)
        author_lbl.setStyleSheet(
            "color: rgba(255, 176, 32, 0.55); background: transparent; border: none;"
        )

        meta.addWidget(title_lbl)
        meta.addWidget(author_lbl)

        hdr.addWidget(icon_lbl, 0, Qt.AlignmentFlag.AlignTop)
        hdr.addLayout(meta, 1)
        root.addLayout(hdr)
        root.addSpacing(10)

        root.addWidget(_make_separator("rgba(255, 176, 32, 0.12)"))
        root.addSpacing(10)

        desc_lbl = QLabel(description)
        desc_lbl.setFont(f_desc)
        desc_lbl.setWordWrap(True)
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        desc_lbl.setStyleSheet(
            "color: rgba(255,255,255,0.50); background: transparent; border: none;"
        )
        fm_d = QtGui.QFontMetrics(f_desc)
        desc_lbl.setFixedHeight(fm_d.height() * 5 + 4)
        root.addWidget(desc_lbl)

        root.addStretch(1)

        badge_row = QHBoxLayout()
        badge_row.setContentsMargins(0, 0, 0, 0)

        count_tpl = self.translations.get("gw_card_entries", "📖  {count} entries")
        count_lbl = QLabel(count_tpl.format(count=entry_count))
        count_lbl.setFont(f_badge)
        count_lbl.setStyleSheet("""
            color: #FFB020;
            background: rgba(255, 176, 32, 0.08);
            border: 1px solid rgba(255, 176, 32, 0.22);
            border-radius: 7px;
            padding: 2px 8px;
        """)
        badge_row.addWidget(count_lbl)
        badge_row.addStretch()
        root.addLayout(badge_row)
        root.addSpacing(8)

        btn_text = self.translations.get("gw_card_add_lorebook", "Add to Library")
        self.add_btn = QPushButton(btn_text)
        self.add_btn.setFixedHeight(32)
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.add_btn.setFont(f_btn)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 176, 32, 0.10);
                border: 1px solid rgba(255, 176, 32, 0.28);
                border-radius: 10px;
                color: #FFB020;
            }
            QPushButton:hover {
                background: rgba(255, 176, 32, 0.22);
                border-color: rgba(255, 176, 32, 0.56);
                color: #FFE082;
            }
            QPushButton:pressed {
                background: rgba(255, 176, 32, 0.34);
                border-color: rgba(255, 176, 32, 0.70);
            }
        """)
        self.add_btn.clicked.connect(
            lambda: asyncio.ensure_future(
                self.import_method(self.title, self.download_url)
            )
        )
        root.addWidget(self.add_btn)

    def _apply_style(self, hover: bool) -> None:
        s = self._HOVER if hover else self._NORMAL
        self.setStyleSheet(f"""
            QFrame#LorebookCard {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {s['bg0']}, stop:1 {s['bg1']}
                );
                border: 1px solid {s['border']};
                border-radius: 16px;
            }}
        """)

    def enterEvent(self, event):
        self._apply_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_style(False)
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            clicked_widget = self.childAt(event.pos())
            if clicked_widget == self.add_btn:
                super().mouseReleaseEvent(event)
                return
            
            dialog = GatewayPreviewDialog(
                title=self.title,
                author=self.author,
                description=self.description,
                download_url=self.download_url,
                asset_type="lorebook",
                import_method=self.import_method,
                parent=self.window()
            )
            dialog.exec()
 
class SceneGatewayCard(QFrame):
    """
    Gateway card for scene/stage entries.
    """
    _NORMAL = dict(
        bg0="rgba(18, 36, 28, 0.52)",
        bg1="rgba(8,  18, 14, 0.72)",
        border="rgba(0, 230, 118, 0.14)",
    )
    _HOVER = dict(
        bg0="rgba(26, 52, 40, 0.68)",
        bg1="rgba(12, 26, 20, 0.88)",
        border="rgba(0, 230, 118, 0.50)",
    )

    def __init__(
        self,
        title: str,
        author: str,
        description: str,
        starting_location: str,
        download_url: str,
        import_method,
        translations: dict,
        parent=None,
    ):
        super().__init__(parent)
        self.title = title
        self.author = author
        self.description = description
        self.starting_location = starting_location
        self.download_url = download_url
        self.import_method = import_method
        self.translations = translations

        self.setFixedSize(230, 298)
        self.setObjectName("SceneCard")
        self._apply_style(False)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 230, 118, 28))
        shadow.setOffset(0, 5)
        self.setGraphicsEffect(shadow)

        W = QtGui.QFont.Weight
        f_title  = _mk_font(11, W.Bold)
        f_author = _mk_font(7,  W.Medium)
        f_desc   = _mk_font(8,  W.Normal)
        f_badge  = _mk_font(8,  W.Bold)
        f_btn    = _mk_font(9,  W.Bold)

        root = QVBoxLayout(self)
        root.setContentsMargins(15, 14, 15, 13)
        root.setSpacing(0)

        hdr = QHBoxLayout()
        hdr.setSpacing(10)
        hdr.setContentsMargins(0, 0, 0, 0)

        icon_lbl = QLabel()
        pix = QPixmap("app/gui/icons/soul_stage.png")
        if not pix.isNull():
            icon_lbl.setPixmap(
                pix.scaled(28, 28,
                           Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
            )
        icon_lbl.setFixedSize(28, 28)
        icon_lbl.setStyleSheet("background: transparent; border: none;")

        meta = QVBoxLayout()
        meta.setSpacing(2)
        meta.setContentsMargins(0, 0, 0, 0)

        title_lbl = QLabel(title)
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet(
            "color: rgba(255,255,255,0.95); background: transparent; border: none;"
        )
        
        fm_t = QtGui.QFontMetrics(_mk_font(11, W.Bold))
        max_title_height = fm_t.height() * 2 + 2
        
        _fit_font_to_label(title_lbl, title, 135, max_title_height, 11, W.Bold)

        author_tpl = self.translations.get("gw_card_author_prefix", "by {author}")
        author_lbl = QLabel(author_tpl.format(author=author))
        author_lbl.setFont(f_author)
        author_lbl.setStyleSheet(
            "color: rgba(0, 230, 118, 0.55); background: transparent; border: none;"
        )

        meta.addWidget(title_lbl)
        meta.addWidget(author_lbl)

        hdr.addWidget(icon_lbl, 0, Qt.AlignmentFlag.AlignTop)
        hdr.addLayout(meta, 1)
        root.addLayout(hdr)
        root.addSpacing(10)

        root.addWidget(_make_separator("rgba(0, 230, 118, 0.12)"))
        root.addSpacing(10)

        desc_lbl = QLabel(description)
        desc_lbl.setFont(f_desc)
        desc_lbl.setWordWrap(True)
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        desc_lbl.setStyleSheet(
            "color: rgba(255,255,255,0.50); background: transparent; border: none;"
        )
        fm_d = QtGui.QFontMetrics(f_desc)
        desc_lbl.setFixedHeight(fm_d.height() * 5 + 4)
        root.addWidget(desc_lbl)

        root.addStretch(1)

        badge_row = QHBoxLayout()
        badge_row.setContentsMargins(0, 0, 0, 0)

        fm_b = QtGui.QFontMetrics(f_badge)
        elided_loc = fm_b.elidedText(
            starting_location, Qt.TextElideMode.ElideRight, 160
        )
        
        loc_tpl = self.translations.get("gw_card_location", "📍  {location}")
        loc_lbl = QLabel(loc_tpl.format(location=elided_loc))
        loc_lbl.setFont(f_badge)
        loc_lbl.setStyleSheet("""
            color: #00E676;
            background: rgba(0, 230, 118, 0.08);
            border: 1px solid rgba(0, 230, 118, 0.22);
            border-radius: 7px;
            padding: 2px 8px;
        """)
        badge_row.addWidget(loc_lbl)
        badge_row.addStretch()
        root.addLayout(badge_row)
        root.addSpacing(8)

        btn_text = self.translations.get("gw_card_add_scene", "Add to Stages")
        self.add_btn = QPushButton(btn_text)
        self.add_btn.setFixedHeight(32)
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.add_btn.setFont(f_btn)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 230, 118, 0.10);
                border: 1px solid rgba(0, 230, 118, 0.28);
                border-radius: 10px;
                color: #00E676;
            }
            QPushButton:hover {
                background: rgba(0, 230, 118, 0.22);
                border-color: rgba(0, 230, 118, 0.56);
                color: #A7FFEB;
            }
            QPushButton:pressed {
                background: rgba(0, 230, 118, 0.34);
                border-color: rgba(0, 230, 118, 0.70);
            }
        """)
        self.add_btn.clicked.connect(
            lambda: asyncio.ensure_future(
                self.import_method(self.title, self.download_url)
            )
        )
        root.addWidget(self.add_btn)

    def _apply_style(self, hover: bool) -> None:
        s = self._HOVER if hover else self._NORMAL
        self.setStyleSheet(f"""
            QFrame#SceneCard {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {s['bg0']}, stop:1 {s['bg1']}
                );
                border: 1px solid {s['border']};
                border-radius: 16px;
            }}
        """)

    def enterEvent(self, event):
        self._apply_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_style(False)
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            clicked_widget = self.childAt(event.pos())
            if clicked_widget == self.add_btn:
                super().mouseReleaseEvent(event)
                return
            
            dialog = GatewayPreviewDialog(
                title=self.title,
                author=self.author,
                description=self.description,
                download_url=self.download_url,
                asset_type="scene",
                import_method=self.import_method,
                parent=self.window()
            )
            dialog.exec()

class GatewayPreviewDialog(QDialog):
    def __init__(self, title: str, author: str, description: str, download_url: str, asset_type: str, import_method, parent=None):
        super().__init__(parent)
        self.asset_title = title
        self.author = author
        self.description = description
        self.download_url = download_url
        self.asset_type = asset_type
        self.import_method = import_method

        self.configuration_settings = configuration.ConfigurationSettings()
        self.translations = {}
        selected_language = self.configuration_settings.get_main_setting("program_language")
        match selected_language:
            case 0:
                self.load_translation("en")
            case 1:
                self.load_translation("ru")
            case _:
                self.load_translation("en")
        
        if self.asset_type == "lorebook":
            self.accent_color = "#FFB020"
            self.accent_glow = "rgba(255, 176, 32, 0.16)"
            self.accent_border = "rgba(255, 176, 32, 0.28)"
            self.text_glow = "#FFE082"
        else:
            self.accent_color = "#00E676"
            self.accent_glow = "rgba(0, 230, 118, 0.16)"
            self.accent_border = "rgba(0, 230, 118, 0.28)"
            self.text_glow = "#A7FFEB"

        self.setFixedSize(640, 560)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setup_ui()
        
        asyncio.create_task(self.fetch_preview_details())

    def load_translation(self, language):
        file_path = f"app/translations/{language}.yaml"
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                self.translations = yaml.safe_load(file)
        else:
            self.translations = {}
            
    def setup_ui(self):
        self.central_container = QFrame(self)
        self.central_container.setObjectName("CentralContainer")
        self.central_container.setFixedSize(640, 560)
        self.central_container.setStyleSheet(f"""
            QFrame#CentralContainer {{
                background-color: #0C0C10;
                border: 1px solid {self.accent_border};
                border-radius: 20px;
            }}
        """)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setColor(QColor(self.accent_color))
        shadow.setOffset(0, 0)
        self.central_container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.central_container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        hdr_layout = QHBoxLayout()
        hdr_layout.setContentsMargins(0, 0, 0, 0)
        
        title_lbl = QLabel(self.asset_title)
        title_lbl.setFont(_mk_font(15, QtGui.QFont.Weight.Bold))
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")
        hdr_layout.addWidget(title_lbl, 1)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setFont(_mk_font(10, QtGui.QFont.Weight.Bold))
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.04);
                color: rgba(255, 255, 255, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 14px;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.2);
                border-color: rgba(239, 68, 68, 0.4);
                color: #FCA5A5;
            }
        """)
        close_btn.clicked.connect(self.close)
        hdr_layout.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(hdr_layout)

        type_str = self.translations.get("gw_preview_type_lorebook", "LOREBOOK") if self.asset_type == "lorebook" else self.translations.get("gw_preview_type_scene", "STAGE SCENARIO")
        author_lbl = QLabel(f"by {self.author}  ·  {type_str}")
        author_lbl.setFont(_mk_font(9, QtGui.QFont.Weight.Bold))
        author_lbl.setStyleSheet(f"color: {self.accent_color}; letter-spacing: 0.8px; text-transform: uppercase;")
        layout.addWidget(author_lbl)
        
        layout.addWidget(_make_separator("rgba(255,255,255,0.06)"))

        desc_lbl = QLabel(self.description)
        desc_lbl.setFont(_mk_font(10, QtGui.QFont.Weight.Normal))
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: rgba(255,255,255,0.65); background: transparent; border: none; line-height: 1.4;")
        layout.addWidget(desc_lbl)

        layout.addSpacing(4)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { background: transparent; width: 6px; margin: 0; }
            QScrollBar::handle:vertical { background: rgba(255, 255, 255, 0.1); border-radius: 3px; min-height: 30px; }
            QScrollBar::handle:vertical:hover { background: rgba(255, 255, 255, 0.18); }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 10, 0)
        self.scroll_layout.setSpacing(14)

        self.loading_label = QLabel(self.translations.get("gw_preview_loading", "Establishing secure uplink...\nRetrieving asset documentation data..."))
        self.loading_label.setFont(_mk_font(11, QtGui.QFont.Weight.Medium))
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("color: rgba(255, 255, 255, 0.3); padding: 40px; line-height: 1.5;")
        self.scroll_layout.addWidget(self.loading_label)

        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area, 1)

        layout.addWidget(_make_separator("rgba(255,255,255,0.06)"))

        ftr_layout = QHBoxLayout()
        ftr_layout.setContentsMargins(0, 5, 0, 5)

        cancel_btn = QPushButton(self.translations.get("gw_preview_btn_close", "Close"))
        cancel_btn.setFixedHeight(36)
        cancel_btn.setFixedWidth(110)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        cancel_btn.setFont(_mk_font(10, QtGui.QFont.Weight.Bold))
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                color: rgba(255, 255, 255, 0.4);
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.04);
                border-color: rgba(255, 255, 255, 0.16);
                color: rgba(255, 255, 255, 0.8);
            }
        """)
        cancel_btn.clicked.connect(self.close)

        self.import_btn = QPushButton(self.translations.get("gw_preview_btn_import", "Import to System"))
        self.import_btn.setFixedHeight(36)
        self.import_btn.setFixedWidth(160)
        self.import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.import_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.import_btn.setFont(_mk_font(10, QtGui.QFont.Weight.Bold))
        self.import_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.accent_glow};
                border: 1px solid {self.accent_border};
                border-radius: 10px;
                color: {self.accent_color};
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.15);
                border-color: {self.accent_color};
                color: {self.text_glow};
            }}
            QPushButton:pressed {{
                background: rgba(0, 0, 0, 0.3);
            }}
        """)
        self.import_btn.clicked.connect(self._trigger_import)

        ftr_layout.addWidget(cancel_btn)
        ftr_layout.addStretch()
        ftr_layout.addWidget(self.import_btn)
        layout.addLayout(ftr_layout)

        self._drag_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    async def fetch_preview_details(self):
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(self.download_url, timeout=10) as response:
                    if response.status != 200:
                        raise Exception(f"Connection state rejected: {response.status}")
                    data = await response.json(content_type=None)

            self.loading_label.hide()
            self.populate_content(data)
        except Exception as e:
            logger.error(f"Failed to fetch asset preview details: {e}")
            err_tpl = self.translations.get("gw_preview_error", "Database connection failed\nCould not fetch asset details:\n{error}")
            self.loading_label.setText(err_tpl.format(error=str(e)))

    def populate_content(self, data: dict):
        if self.asset_type == "lorebook":
            entries = data.get("entries", [])
            
            summary_tpl = self.translations.get("gw_preview_lorebook_summary", "Dataset contains {count} cognitive rules:")
            meta_lbl = QLabel(summary_tpl.format(count=len(entries)))
            meta_lbl.setFont(_mk_font(10, QtGui.QFont.Weight.Bold))
            meta_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.9); margin-bottom: 5px;")
            self.scroll_layout.addWidget(meta_lbl)

            default_name = self.translations.get("gw_preview_unnamed", "Unnamed Entry")
            for i, entry in enumerate(entries):
                entry_frame = QFrame()
                entry_frame.setStyleSheet(f"""
                    QFrame {{
                        background-color: rgba(255, 176, 32, 0.02);
                        border: 1px solid rgba(255, 176, 32, 0.08);
                        border-radius: 10px;
                    }}
                """)
                ef_layout = QVBoxLayout(entry_frame)
                ef_layout.setContentsMargins(14, 12, 14, 12)
                ef_layout.setSpacing(6)

                rule_name = QLabel(f"{i+1}. {entry.get('name', default_name)}")
                rule_name.setFont(_mk_font(11, QtGui.QFont.Weight.Bold))
                rule_name.setStyleSheet("color: #FFFFFF; border: none; background: transparent;")
                ef_layout.addWidget(rule_name)

                meta_row = QHBoxLayout()
                trig_text = self.translations.get("gw_preview_trigger", "Trigger")
                t_lbl = QLabel(f"{trig_text}: {entry.get('trigger_type', 'keyword').upper()}")
                t_lbl.setFont(_mk_font(8, QtGui.QFont.Weight.Bold))
                t_lbl.setStyleSheet(f"color: {self.accent_color}; background: transparent; border: none;")
                meta_row.addWidget(t_lbl)

                if entry.get("key"):
                    keys_text = self.translations.get("gw_preview_keys", "Keys")
                    k_lbl = QLabel(f"{keys_text}: {', '.join(entry.get('key'))}")
                    k_lbl.setFont(_mk_font(8, QtGui.QFont.Weight.Medium))
                    k_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.35); background: transparent; border: none;")
                    meta_row.addWidget(k_lbl, 1)
                meta_row.addStretch()
                ef_layout.addLayout(meta_row)

                rule_prompt = QTextEdit()
                rule_prompt.setPlainText(entry.get("content", ""))
                rule_prompt.setReadOnly(True)
                rule_prompt.setFont(_mk_font(9, QtGui.QFont.Weight.Normal))
                rule_prompt.setStyleSheet(f"""
                    QTextEdit {{
                        background: rgba(0, 0, 0, 0.25);
                        color: rgba(255, 255, 255, 0.55);
                        border: 1px solid rgba(255, 255, 255, 0.04);
                        border-radius: 6px;
                        padding: 6px;
                    }}
                """)
                
                fm = QtGui.QFontMetrics(rule_prompt.font())
                h = fm.boundingRect(entry.get("content", "")).width() // 500
                rule_prompt.setFixedHeight(max(60, min(140, h * 16 + 20)))
                
                ef_layout.addWidget(rule_prompt)
                self.scroll_layout.addWidget(entry_frame)

        else:
            def add_block(sec_title: str, text: str):
                if not text: return
                
                lbl = QLabel(sec_title)
                lbl.setFont(_mk_font(9, QtGui.QFont.Weight.Bold))
                lbl.setStyleSheet(f"color: {self.accent_color}; letter-spacing: 0.8px; margin-top: 5px;")
                self.scroll_layout.addWidget(lbl)
                
                txt = QTextEdit()
                txt.setPlainText(text)
                txt.setReadOnly(True)
                txt.setFont(_mk_font(10, QtGui.QFont.Weight.Normal))
                txt.setStyleSheet("""
                    QTextEdit {
                        background-color: rgba(0, 0, 0, 0.25);
                        color: rgba(255, 255, 255, 0.7);
                        border: 1px solid rgba(255, 255, 255, 0.05);
                        border-radius: 8px;
                        padding: 10px;
                        line-height: 1.4;
                    }
                """)
                
                fm = QtGui.QFontMetrics(txt.font())
                h = fm.boundingRect(text).width() // 520
                txt.setMinimumHeight(max(80, min(220, h * 16 + 30)))
                
                self.scroll_layout.addWidget(txt)

            add_block(self.translations.get("gw_preview_header_context", "WORLD CONTEXT & SCENARIO"), data.get("world_context", ""))
            add_block(self.translations.get("gw_preview_header_narration", "OPENING NARRATION"), data.get("opening_narration", ""))
            
            stat_row = QHBoxLayout()
            stat_row.setSpacing(10)
            
            if data.get("gm_tone"):
                tone_text = self.translations.get("gw_preview_tone", "Tone")
                tone_lbl = QLabel(f"{tone_text}:  {str(data['gm_tone']).upper()}")
                tone_lbl.setFont(_mk_font(8, QtGui.QFont.Weight.Bold))
                tone_lbl.setStyleSheet(f"color: {self.accent_color}; background: rgba(0,230,118,0.06); border: 1px solid rgba(0,230,118,0.18); border-radius: 6px; padding: 4px 10px;")
                stat_row.addWidget(tone_lbl)
                
            if data.get("time_of_day"):
                time_text = self.translations.get("gw_preview_time", "Time")
                tod_lbl = QLabel(f"{time_text}:  {str(data['time_of_day']).upper()}")
                tod_lbl.setFont(_mk_font(8, QtGui.QFont.Weight.Bold))
                tod_lbl.setStyleSheet(f"color: #FFFFFF; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 4px 10px;")
                stat_row.addWidget(tod_lbl)
                
            stat_row.addStretch()
            self.scroll_layout.addLayout(stat_row)

            add_block(self.translations.get("gw_preview_header_style", "NARRATOR STYLE"), data.get("narrator_style", ""))

        self.scroll_layout.addStretch()

    def _trigger_import(self):
        self.close()
        asyncio.ensure_future(self.import_method(self.asset_title, self.download_url))

AVATAR_GRADIENTS = [
    ("#FF7A7A", "#E33D3D"),
    ("#5EEAD4", "#0D9488"),
    ("#C4B5FD", "#7C3AED"),
    ("#93C5FD", "#2563EB"),
    ("#FDE68A", "#D97706"),
    ("#86EFAC", "#16A34A"),
    ("#F9A8D4", "#DB2777"),
    ("#A5B4FC", "#4F46E5"),
]

class ModelListItemWidget(QWidget):
    def __init__(self, model_name, file_size_bytes, full_path, refresh_method,
                 launch_server_method, stop_server_method, ui, parent=None,
                 is_server_running=False):
        super().__init__(parent)
        self.configuration_settings = configuration.ConfigurationSettings()

        self.translations = {}
        selected_language = self.configuration_settings.get_main_setting("program_language")
        match selected_language:
            case 0:
                self.load_translation("en")
            case 1:
                self.load_translation("ru")
            case _:
                self.load_translation("en")

        self.model_name = model_name or "unknown_model"
        self.full_path = full_path or ""
        self.refresh_method = refresh_method
        self.launch_server_method = launch_server_method
        self.stop_server_method = stop_server_method
        self.ui = ui
        self.parent_widget = parent
        self.is_server_running = is_server_running

        current_default_path = self.configuration_settings.get_main_setting("local_llm")
        current_default_name = None
        if current_default_path and os.path.exists(current_default_path):
            current_default_name = os.path.splitext(os.path.basename(current_default_path))[0]
        self.is_default = current_default_name == self.model_name

        if self.is_default and is_server_running:
            self.server_loaded = True
        else:
            self.server_loaded = False

        self.setFixedHeight(72)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(6, 4, 6, 4)
        outer_layout.setSpacing(0)

        self.card = QFrame(self)
        self.card.setObjectName("card")
        self._apply_card_style(hover=False)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(18)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 3)
        self.card.setGraphicsEffect(shadow)

        card_layout = QHBoxLayout(self.card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        self.accent_bar = QFrame()
        self.accent_bar.setFixedWidth(4)
        self.accent_bar.setFixedHeight(32)
        card_layout.addWidget(self.accent_bar)
        self._update_accent_bar()

        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(12, 8, 12, 8)
        content_layout.setSpacing(12)
        card_layout.addWidget(content, stretch=1)

        avatar_box = QWidget()
        avatar_box.setFixedSize(40, 40)
        avatar_grid = QGridLayout(avatar_box)
        avatar_grid.setContentsMargins(0, 0, 0, 0)
        avatar_grid.setSpacing(0)

        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(40, 40)
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c1, c2 = self._avatar_colors(self.model_name)
        border = "border: 2px solid rgba(255,215,0,0.85);" if self.is_default else "border: none;"
        self.avatar_label.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {c1}, stop:1 {c2});
                border-radius: 20px;
                {border}
                color: white;
                font-family: 'Inter Tight SemiBold';
                font-size: 15px;
                font-weight: bold;
            }}
        """)
        self.avatar_label.setText(self.model_name[:1].upper() if self.model_name else "?")
        avatar_grid.addWidget(self.avatar_label, 0, 0)

        if self.is_default:
            star_badge = QLabel()
            font = QtGui.QFont()
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            star_badge.setFont(font)
            star_badge.setFixedSize(16, 16)
            star_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            star_pix = QPixmap("app/gui/icons/star.png")
            if not star_pix.isNull():
                star_badge.setPixmap(star_pix.scaled(
                    11, 11, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
            else:
                star_badge.setText("★")
                star_badge.setStyleSheet(star_badge.styleSheet() + "color: #FFD700; font-size: 9px;")
            star_badge.setStyleSheet(star_badge.styleSheet() + """
                background-color: #1c1c22;
                border: 1px solid rgba(255,215,0,0.6);
                border-radius: 8px;
            """)
            avatar_grid.addWidget(
                star_badge, 0, 0,
                alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight
            )

        content_layout.addWidget(avatar_box)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        self.name_label = QLabel(self.model_name)
        font_name = QtGui.QFont("Inter Tight SemiBold", 11, QtGui.QFont.Weight.Bold)
        font_name.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.name_label.setFont(font_name)
        name_color = "#FFD86B" if self.is_default else "rgba(255, 255, 255, 0.92)"
        self.name_label.setStyleSheet(f"color: {name_color}; background: transparent; border: none;")
        info_layout.addWidget(self.name_label)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(6)

        size_str = self.human_readable_size(file_size_bytes)
        self.size_badge = QLabel(size_str)
        self.size_badge.setStyleSheet(self._pill_style("rgba(255,255,255,0.06)", "rgba(255,255,255,0.55)"))
        font = QtGui.QFont()
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.size_badge.setFont(font)
        meta_row.addWidget(self.size_badge)

        self.status_badge = QLabel()
        font = QtGui.QFont()
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.status_badge.setFont(font)
        if self.is_default:
            if is_server_running:
                self.status_badge.setText("●  Running")
                self.status_badge.setStyleSheet(self._pill_style("rgba(76,175,80,0.15)", "#81C784"))
            else:
                self.status_badge.setText("○  Standby")
                self.status_badge.setStyleSheet(self._pill_style("rgba(255,255,255,0.05)", "rgba(255,255,255,0.5)"))
            meta_row.addWidget(self.status_badge)
        else:
            self.status_badge.hide()

        meta_row.addStretch()
        info_layout.addLayout(meta_row)
        content_layout.addLayout(info_layout, stretch=1)

        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(6)

        btn_font = QtGui.QFont("Inter Tight SemiBold", 9)
        btn_font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

        self.btn_set_default = QPushButton("★  " + self.translations.get("button_set_default", "Set Default"))
        self.btn_set_default.setFont(btn_font)
        self.btn_set_default.setFixedHeight(30)
        self.btn_set_default.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_set_default.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self._style_secondary_pill(self.btn_set_default)
        self.btn_set_default.clicked.connect(self.on_set_default_clicked)

        if self.server_loaded:
            label = self.translations.get("button_disable_server", "Unload")
        else:
            label = self.translations.get("button_launch_server", "Load")
        self.btn_launch_server = QPushButton(label)
        self.btn_launch_server.setFont(btn_font)
        self.btn_launch_server.setFixedHeight(30)
        self.btn_launch_server.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_launch_server.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self._style_primary_button(self.btn_launch_server, active=self.server_loaded)
        if self.server_loaded:
            self.btn_launch_server.clicked.connect(self.on_unload_model_clicked)
        else:
            self.btn_launch_server.clicked.connect(self.on_launch_server_clicked)

        if self.is_default:
            actions_layout.addWidget(self.btn_launch_server)
        else:
            actions_layout.addWidget(self.btn_set_default)

        divider = QFrame()
        divider.setFixedSize(1, 20)
        divider.setStyleSheet("background-color: rgba(255,255,255,0.08); border: none;")
        actions_layout.addWidget(divider)

        self.btn_open_file = self._icon_button(
            "app/gui/icons/folder.png", 15, "Open file location in Explorer"
        )
        self.btn_open_file.clicked.connect(self.on_open_file_location_clicked)
        actions_layout.addWidget(self.btn_open_file)

        self.btn_delete = self._icon_button(
            "app/gui/icons/bin.png", 15,
            self.translations.get("button_delete_model", "Delete model"),
            danger=True
        )
        self.btn_delete.clicked.connect(self.on_delete_clicked)
        actions_layout.addWidget(self.btn_delete)

        content_layout.addLayout(actions_layout)

        outer_layout.addWidget(self.card)
        self.setLayout(outer_layout)
 
    def _avatar_colors(self, name):
        idx = int(hashlib.md5(name.encode("utf-8")).hexdigest(), 16) % len(AVATAR_GRADIENTS)
        return AVATAR_GRADIENTS[idx]
 
    def _pill_style(self, bg, color):
        return f"""
            QLabel {{
                background-color: {bg};
                color: {color};
                border-radius: 6px;
                padding: 2px 8px;
                font-size: 10px;
                font-family: 'Inter Tight Medium';
            }}
        """
 
    def _apply_card_style(self, hover):
        bg = "rgba(255, 255, 255, 0.055)" if hover else "rgba(255, 255, 255, 0.03)"
        if hover and self.is_default:
            border = "rgba(255, 215, 0, 0.35)"
        elif hover:
            border = "rgba(255, 255, 255, 0.16)"
        else:
            border = "rgba(255, 255, 255, 0.06)"
        self.card.setStyleSheet(f"""
            QFrame#card {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 14px;
            }}
        """)
 
    def _update_accent_bar(self):
        if self.is_default and self.is_server_running:
            color = "qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #66BB6A, stop:1 #2E7D32)"
        elif self.is_default:
            color = "qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #FFD86B, stop:1 #D97706)"
        else:
            color = "rgba(255,255,255,0.05)"
        self.accent_bar.setStyleSheet(f"""
            QFrame {{
                background: {color};
                border-top-left-radius: 14px;
                border-bottom-left-radius: 14px;
            }}
        """)
 
    def _style_primary_button(self, btn, active):
        if active:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(230, 81, 0, 0.18);
                    color: #FFCC80;
                    border-radius: 8px;
                    border: 1px solid rgba(255, 152, 0, 0.35);
                    padding: 0px 14px;
                }
                QPushButton:hover {
                    background-color: rgba(230, 81, 0, 0.35);
                    border: 1px solid rgba(255, 152, 0, 0.6);
                    color: #ffffff;
                }
                QPushButton:pressed { background-color: rgba(230, 81, 0, 0.12); }
            """)
        else:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(46, 125, 50, 0.18);
                    color: #A5D6A7;
                    border-radius: 8px;
                    border: 1px solid rgba(76, 175, 80, 0.35);
                    padding: 0px 14px;
                }
                QPushButton:hover {
                    background-color: rgba(46, 125, 50, 0.35);
                    border: 1px solid rgba(76, 175, 80, 0.6);
                    color: #ffffff;
                }
                QPushButton:pressed { background-color: rgba(46, 125, 50, 0.12); }
            """)
 
    def _style_secondary_pill(self, btn):
        btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.8);
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.12);
                padding: 0px 14px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
                border: 1px solid rgba(255, 255, 255, 0.3);
                color: #ffffff;
            }
            QPushButton:pressed { background-color: rgba(255, 255, 255, 0.08); }
        """)
 
    def _icon_button(self, icon_path, icon_size, tooltip, danger=False):
        btn = QPushButton()
        btn.setToolTip(tooltip)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(icon_path), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        btn.setIcon(icon)
        btn.setIconSize(QtCore.QSize(icon_size, icon_size))
        btn.setFixedSize(30, 30)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        if danger:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(211, 47, 47, 0.08);
                    border-radius: 8px;
                    border: 1px solid rgba(244, 67, 54, 0.18);
                }
                QPushButton:hover {
                    background-color: rgba(211, 47, 47, 0.28);
                    border: 1px solid rgba(244, 67, 54, 0.5);
                }
                QPushButton:pressed { background-color: rgba(211, 47, 47, 0.05); }
            """)
        else:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.04);
                    border-radius: 8px;
                    border: 1px solid rgba(255, 255, 255, 0.10);
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.14);
                    border: 1px solid rgba(255, 255, 255, 0.28);
                }
                QPushButton:pressed { background-color: rgba(255, 255, 255, 0.04); }
            """)
        return btn
 
    def load_translation(self, language):
        file_path = f"app/translations/{language}.yaml"
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                self.translations = yaml.safe_load(file)
        else:
            self.translations = {}
 
    def human_readable_size(self, size_bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} TB"
 
    def on_set_default_clicked(self):
        self.configuration_settings.update_main_setting("local_llm", self.full_path)
        self.refresh_method()
 
    def on_launch_server_clicked(self):
        self.btn_launch_server.setText(self.translations.get("button_disable_server", "Unload"))
        QApplication.processEvents()
        self.server_loaded = True
        self.is_server_running = True
        self._style_primary_button(self.btn_launch_server, active=True)
        self._update_accent_bar()
 
        try:
            self.btn_launch_server.clicked.disconnect()
        except (TypeError, RuntimeError):
            pass
 
        self.btn_launch_server.clicked.connect(self.on_unload_model_clicked)
        self.launch_server_method()
 
    def on_unload_model_clicked(self):
        self.btn_launch_server.setText(self.translations.get("button_launch_server", "Load"))
        QApplication.processEvents()
        self.server_loaded = False
        self.is_server_running = False
        self._style_primary_button(self.btn_launch_server, active=False)
        self._update_accent_bar()
 
        try:
            self.btn_launch_server.clicked.disconnect()
        except (TypeError, RuntimeError):
            pass
 
        self.btn_launch_server.clicked.connect(self.on_launch_server_clicked)
        self.stop_server_method()
 
    def on_delete_clicked(self):
        model_name = self.model_name
 
        title = self.translations.get("delete_model", "Delete LLM")
        first_text = self.translations.get("model_widget_delete", "Do you want to delete the model:")
        second_text = self.translations.get("model_widget_delete_2", "This action cannot be canceled.")
 
        message_text = f"{first_text} '{model_name}'?\n\n{second_text}"
 
        parent_win = self.window() if hasattr(self, "window") else self
 
        dialog = SowConfirmDialog(
            parent=parent_win,
            title=title,
            text=message_text,
            confirm_text="Delete",
            danger=True
        )
 
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            try:
                os.remove(self.full_path)
                self.refresh_method()
 
                sow_toast(
                    parent=parent_win,
                    title="Deleted",
                    text="Model deleted successfully.",
                    msg_type="success"
                )
            except Exception as e:
                sow_toast(
                    parent=parent_win,
                    title="Delete Error",
                    text=f"Couldn't delete the model:\n{str(e)}",
                    msg_type="error"
                )
 
    def enterEvent(self, event):
        self._apply_card_style(hover=True)
        super().enterEvent(event)
 
    def leaveEvent(self, event):
        self._apply_card_style(hover=False)
        super().leaveEvent(event)
 
    def on_open_file_location_clicked(self):
        try:
            subprocess.Popen(["explorer", "/select,", os.path.abspath(self.full_path)])
        except Exception as e:
            parent_win = self.window() if hasattr(self, "window") else self
 
            sow_toast(
                parent=parent_win,
                title="Error",
                text=f"Cannot open file location:\n{str(e)}",
                msg_type="error"
            )

class PersonaItemWidget(QWidget):
    def __init__(self, name="", main_name="", description="", avatar_path=None, 
                 is_plus_item=False, open_editor_method=None, open_editor_by_name_method=None, 
                 refresh_method=None, parent=None, default_btn_translation="Set as default", delete_btn_translation="Delete"):
        super().__init__(parent)
        self.setFixedHeight(80)
        self.configuration_settings = configuration.ConfigurationSettings()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)

        self.name = name
        self.main_name = main_name
        self.open_editor_method = open_editor_method
        self.open_editor_by_name_method = open_editor_by_name_method
        self.refresh_method = refresh_method

        self.name_label = QLabel(name)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(9)
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.name_label.setFont(font)
        self.name_label.setStyleSheet("font-weight: bold; font-size: 12pt;")

        if not is_plus_item:
            self.avatar_label = QLabel()
            if avatar_path and os.path.exists(avatar_path):
                pixmap = QtGui.QPixmap(avatar_path).scaled(
                    60, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                )
            else:
                pixmap = QtGui.QPixmap("app/gui/icons/person.png").scaled(
                    60, 60, Qt.AspectRatioMode.KeepAspectRatio
                )
            mask = QPixmap(pixmap.size())
            mask.fill(QtCore.Qt.GlobalColor.transparent)

            painter = QPainter(mask)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QtCore.Qt.GlobalColor.black)
            painter.setPen(QtCore.Qt.GlobalColor.transparent)
            painter.drawEllipse(0, 0, pixmap.width(), pixmap.height())
            painter.end()

            pixmap.setMask(mask.createMaskFromColor(QtCore.Qt.GlobalColor.transparent))
            self.avatar_label.setPixmap(pixmap.scaled(60, 60, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
            self.avatar_label.setFixedSize(60, 60)
            self.avatar_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.avatar_label.setScaledContents(True)

            info_layout = QVBoxLayout()
            info_layout.setSpacing(2)
            info_layout.setContentsMargins(0, 15, 0, 15)

            self.desc_label = QLabel(description)
            self.desc_label.setStyleSheet("font-size: 10pt; color: gray;")

            info_layout.addWidget(self.name_label)
            info_layout.addWidget(self.desc_label)

            self.button_layout = QHBoxLayout()

            current_default_persona = self.configuration_settings.get_user_data("default_persona")
            if not current_default_persona:
                self.configuration_settings.update_user_data("default_persona", "None")
            else:
                if main_name != current_default_persona:
                    self.set_default_button = QPushButton(default_btn_translation)
                    self.set_default_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
                    self.set_default_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                    self.set_default_button.setStyleSheet("""
                        QPushButton {
                            background-color: #2D2D2D;
                            color: #BBBBBB;
                            border-radius: 10px;
                            border: 1px solid #383838;
                            padding: 0;
                        }

                        QPushButton:hover {
                            background-color: #333333;
                            border: 1px solid #404040;
                        }

                        QPushButton:pressed {
                            background-color: #202020;
                            color: #999999;
                        }
                    """)
                    self.set_default_button.setFixedSize(150, 35)
                    self.set_default_button.setObjectName("setdefaultButton")
                    font = QtGui.QFont()
                    font.setFamily("Inter Tight SemiBold")
                    font.setPointSize(7)
                    font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
                    self.set_default_button.setFont(font)
                    try:
                        self.set_default_button.clicked.disconnect()
                    except Exception as e:
                        pass
                    self.set_default_button.clicked.connect(lambda _, n=main_name: self.set_default_persona(n))
                    self.button_layout.addWidget(self.set_default_button)

            self.delete_button = QPushButton(delete_btn_translation)
            self.delete_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            font = QtGui.QFont()
            font.setFamily("Inter Tight SemiBold")
            font.setPointSize(7)
            font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
            self.delete_button.setFont(font)

            self.delete_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            self.delete_button.setFixedSize(130, 35)
            self.delete_button.setStyleSheet("""
                QPushButton {
                    background-color: #D32F2F;
                    color: rgb(227, 227, 227);
                    font-size: 12px;
                    border-radius: 6px;
                    border: 1px solid #9A0007;
                    padding: 5px;
                }

                QPushButton:hover {
                    background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                    stop: 0 #E53935, stop: 1 #C62828);
                    border: 1px solid #B71C1C;
                }

                QPushButton:pressed {
                    background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                    stop: 0 #B71C1C, stop: 1 #E53935);
                    border: 1px solid #7A0000;
                }

                QPushButton:disabled {
                    background-color: #EF9A9A;
                    color: #A8A8A8;
                    border: 1px solid #BDBDBD;
                }
            """)
            self.delete_button.setObjectName("deleteButton")
            self.button_layout.addWidget(self.delete_button)

            self.mousePressEvent = self.on_click_persona

            layout.addWidget(self.avatar_label)
            layout.addLayout(info_layout)
            layout.addLayout(self.button_layout)
        else:
            self.name_label.setText("+")
            self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.name_label.setStyleSheet("font-size: 20pt; font-weight: bold; color: white;")

            self.mousePressEvent = self.on_click

            layout.addWidget(self.name_label)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    def on_click(self, event):
        self.open_editor_method()
    
    def on_click_persona(self, event):
        self.open_editor_by_name_method(self.main_name)

    def set_default_persona(self, name):
        self.configuration_settings.update_user_data("default_persona", name)
        self.refresh_method()

class BackgroundCard(QtWidgets.QFrame):
    def __init__(self, name, image_path, is_selected, click_callback, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 150)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        self.name = name
        self.image_path = image_path
        self.is_selected = is_selected
        self.click_callback = click_callback

        if image_path == "Default":
            self.pixmap = QPixmap(200, 150)
            self.pixmap.fill(QColor(15, 15, 18))
        else:
            original_pixmap = QPixmap(image_path)
            self.pixmap = original_pixmap.scaled(
                200, 150, 
                Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
                Qt.TransformationMode.SmoothTransformation
            )

        self._hover_scale = 1.0
        self.anim_scale = QPropertyAnimation(self, b"hover_scale")
        self.anim_scale.setDuration(200)
        self.anim_scale.setEasingCurve(QEasingCurve.Type.OutCubic)

    @QtCore.pyqtProperty(float)
    def hover_scale(self):
        return self._hover_scale

    @hover_scale.setter
    def hover_scale(self, value):
        self._hover_scale = value
        self.update()

    def enterEvent(self, event):
        self.anim_scale.setEndValue(1.05)
        self.anim_scale.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim_scale.setEndValue(1.0)
        self.anim_scale.start()
        super().leaveEvent(event)

    @safe_paint
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        rect = self.rect()

        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(rect), 12, 12)
        painter.setClipPath(path)

        painter.save()
        painter.translate(rect.center())
        painter.scale(self._hover_scale, self._hover_scale)
        painter.drawPixmap(-self.pixmap.width() // 2, -self.pixmap.height() // 2, self.pixmap)
        painter.restore()

        gradient = QtGui.QLinearGradient(0, rect.height() * 0.5, 0, rect.height())
        gradient.setColorAt(0, QColor(0, 0, 0, 0))
        gradient.setColorAt(1, QColor(0, 0, 0, 200))
        painter.fillRect(rect, QtGui.QBrush(gradient))

        if self.is_selected:
            painter.setPen(QtGui.QPen(QColor(76, 175, 80), 4))
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 10, 10)
        else:
            painter.setPen(QtGui.QPen(QColor(255, 255, 255, 30), 2))
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 11, 11)

        painter.setPen(QColor(255, 255, 255, 240))
        font = QFont("Inter Tight SemiBold", 11, QFont.Weight.Bold)
        painter.setFont(font)
        
        display_name = os.path.splitext(self.name)[0] if self.name != "Default" else self.translations.get("background_changer_default_btn", "Default Theme")
        
        text_rect = QtCore.QRect(10, rect.height() - 35, rect.width() - 20, 30)
        painter.drawText(
            text_rect, 
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextSingleLine, 
            display_name
        )

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.click_callback(self.image_path)
        super().mousePressEvent(event)

class BackgroundChangerWindow(QDialog):
    def __init__(self, ui=None, translation=None, parent=None):
        super().__init__(parent)
        self.translations = translation if translation else {}
        self.ui = ui

        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(940, 540)

        self.configuration_settings = configuration.ConfigurationSettings()
        
        self.current_bg = self.configuration_settings.get_main_setting("chat_background_image")

        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        self.main_frame = QtWidgets.QFrame()
        self.main_frame.setStyleSheet("""
            QFrame#MainFrame {
                background-color: #1e1e1e;
                border: 1px solid #333333;
                border-radius: 15px;
            }
        """)
        self.main_frame.setObjectName("MainFrame")

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setOffset(0, 5)
        shadow.setColor(QColor(0, 0, 0, 150))
        self.main_frame.setGraphicsEffect(shadow)

        frame_layout = QVBoxLayout(self.main_frame)
        frame_layout.setContentsMargins(20, 20, 20, 20)
        frame_layout.setSpacing(15)

        header_layout = QHBoxLayout()
        
        title = QLabel(self.translations.get("background_changer_label_1", "Choose a background for the chat"))
        title.setStyleSheet("font-family: 'Inter Tight SemiBold'; font-size: 18px; color: white;")
        
        close_btn = QPushButton("×")
        font = QtGui.QFont()
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        close_btn.setFont(font)
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #888888;
                font-size: 20px;
                font-weight: bold;
                border-radius: 15px;
            }
            QPushButton:hover {
                background-color: #333333;
                color: #ff6b6b;
            }
        """)
        close_btn.clicked.connect(self.close)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        frame_layout.addLayout(header_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll_area.setStyleSheet("""
            QScrollArea { 
                border: none; 
                background: transparent; 
            }
            QScrollBar:vertical {
                background: transparent;
                width: 0px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: transparent;
                min-height: 0px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        grid_layout = QGridLayout(container)
        grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        grid_layout.setSpacing(15)
        grid_layout.setContentsMargins(5, 5, 5, 5)

        is_default_selected = (self.current_bg == "None" or not self.current_bg)
        default_card = BackgroundCard("Default", "Default", is_default_selected, self.select_background)
        default_card.translations = self.translations
        grid_layout.addWidget(default_card, 0, 0)

        images_directory = "assets/backgrounds"
        if os.path.exists(images_directory):
            image_files = [f for f in os.listdir(images_directory) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            
            row = 0
            col = 1
            max_cols = 4

            for img_file in image_files:
                path = os.path.join(images_directory, img_file).replace("\\", "/")
                
                is_selected = (self.current_bg == path)
                
                card = BackgroundCard(img_file, path, is_selected, self.select_background)
                grid_layout.addWidget(card, row, col)
                
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1

        scroll_area.setWidget(container)
        frame_layout.addWidget(scroll_area)

        main_layout.addWidget(self.main_frame)

    def get_scroll_area_base_style(self):
        return """
            QScrollBar {
                background: transparent;
                background-color: transparent;
            }

            QScrollBar:vertical { 
                background: transparent; 
                width: 6px; 
                margin: 4px 0px 4px 0px;
                border: none;
            }
            QScrollBar::handle:vertical { 
                background-color: rgba(255, 255, 255, 0.15);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 3px; 
                min-height: 40px;
            }
            QScrollBar::handle:vertical:hover { 
                background-color: rgba(255, 255, 255, 0.25); 
                border: 1px solid rgba(255, 255, 255, 0.22);
            }
            QScrollBar::handle:vertical:pressed { 
                background-color: rgba(255, 255, 255, 0.35); 
                border: 1px solid rgba(255, 255, 255, 0.32);
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { 
                background: transparent; 
                border: none;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { 
                background: transparent; 
                border: none; 
                height: 0px;
            }

            QScrollBar:horizontal { 
                background: transparent; 
                height: 8px; 
                border-radius: 4px; 
                border: none;
            }
            QScrollBar::handle:horizontal { 
                background-color: rgba(255, 255, 255, 0.15); 
                border: 1px solid rgba(255, 255, 255, 0.12);
                width: 10px; 
                border-radius: 4px; 
                margin: 1px; 
            }
            QScrollBar::handle:horizontal:hover { 
                background-color: rgba(255, 255, 255, 0.25); 
                border: 1px solid rgba(255, 255, 255, 0.22);
            }
            QScrollBar::handle:horizontal:pressed { 
                background-color: rgba(255, 255, 255, 0.35); 
                border: 1px solid rgba(255, 255, 255, 0.32);
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { 
                border: none; 
                background: transparent; 
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { 
                background: transparent; 
                border: none;
            }
        """

    def select_background(self, image_path):
        base_style = self.get_scroll_area_base_style()

        scroll_area_style_template = f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
                padding: 5px;
                border-radius: 10px;
            }}
            QScrollArea > QWidget, 
            QScrollArea #qt_scrollarea_viewport, 
            QScrollArea QWidget {{
                background: transparent;
                background-color: transparent;
            }}
            {base_style}
        """

        if image_path and image_path != "Default":
            self.ui.chat_page.setStyleSheet(f"""
                QWidget#chat_page {{
                    border-image: url({image_path}) 0 0 0 0 stretch stretch;
                    background-position: center;
                    background-repeat: no-repeat;
                }}
            """)
            self.ui.scrollArea_chat.setStyleSheet(scroll_area_style_template)
            self.configuration_settings.update_main_setting("chat_background_image", image_path)
        else:
            self.ui.chat_page.setStyleSheet(f"""
                QWidget#chat_page {{
                    background-position: center;
                    background-repeat: no-repeat;
                }}
            """)
            self.ui.scrollArea_chat.setStyleSheet(scroll_area_style_template)
            self.configuration_settings.update_main_setting("chat_background_image", "None")

        self.close()

class CharacterCardList(QtWidgets.QFrame):
    def __init__(self, character_name, image_path, icon_api_path, method, parent=None):
        super().__init__(parent)
        self.setFixedSize(210, 270)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.character_name = character_name
        self.open_chat = method
        
        self.pixmap = QtGui.QPixmap(image_path)
        if self.pixmap.isNull():
            self.pixmap = QtGui.QPixmap("app/gui/icons/logotype.png")
            
        self.icon_api_pixmap = QtGui.QPixmap(icon_api_path).scaled(
            20, 20, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation
        )
        
        self.shadow_effect = QtWidgets.QGraphicsDropShadowEffect(self)
        self.shadow_effect.setBlurRadius(15)
        self.shadow_effect.setColor(QtGui.QColor(0, 0, 0, 100))
        self.shadow_effect.setOffset(0, 5)
        self.setGraphicsEffect(self.shadow_effect)

        self._hover_scale = 1.0
        self.anim_scale = QtCore.QPropertyAnimation(self, b"hover_scale")
        self.anim_scale.setDuration(350)
        self.anim_scale.setEasingCurve(QtCore.QEasingCurve.Type.InOutCubic)

        self._darkness_alpha = 100.0
        self.anim_dark = QtCore.QPropertyAnimation(self, b"darkness_alpha")
        self.anim_dark.setDuration(350)
        self.anim_dark.setEasingCurve(QtCore.QEasingCurve.Type.InOutCubic)

        self._info_alpha = 255.0
        self.anim_info = QtCore.QPropertyAnimation(self, b"info_alpha")
        self.anim_info.setDuration(300)
        self.anim_info.setEasingCurve(QtCore.QEasingCurve.Type.InOutCubic)
        
        self.action_panel = QtWidgets.QFrame(self)
        self.action_panel.setStyleSheet("background-color: rgba(15, 15, 15, 0.9); border-radius: 15px;")
        self.action_panel.setGeometry(10, 280, 190, 45) 
        self.action_panel_layout = QtWidgets.QHBoxLayout(self.action_panel)
        self.action_panel_layout.setContentsMargins(5, 0, 5, 0)
        self.action_panel_layout.setSpacing(5)
        
        self.panel_anim = QtCore.QPropertyAnimation(self.action_panel, b"pos")
        self.panel_anim.setDuration(350)
        self.panel_anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)

    @QtCore.pyqtProperty(float)
    def hover_scale(self):
        return self._hover_scale

    @hover_scale.setter
    def hover_scale(self, value):
        self._hover_scale = value
        self.update()

    @QtCore.pyqtProperty(float)
    def darkness_alpha(self):
        return self._darkness_alpha

    @darkness_alpha.setter
    def darkness_alpha(self, value):
        self._darkness_alpha = value
        self.update()

    @QtCore.pyqtProperty(float)
    def info_alpha(self):
        return self._info_alpha

    @info_alpha.setter
    def info_alpha(self, value):
        self._info_alpha = value
        self.update()

    def enterEvent(self, event):
        self.anim_scale.setEndValue(1.05)
        self.anim_dark.setEndValue(0.0)
        self.anim_info.setEndValue(0.0)
        self.panel_anim.setEndValue(QtCore.QPoint(10, 215))
        
        self.anim_scale.start()
        self.anim_dark.start()
        self.anim_info.start()
        self.panel_anim.start()

        if hasattr(self, 'more_btn_anim'):
            self.more_btn_anim.setEndValue(QtCore.QPoint(self.width() - 40, 10))
            self.more_btn_anim.start()
        
        self.shadow_effect.setOffset(0, 8)
        self.shadow_effect.setBlurRadius(25)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim_scale.setEndValue(1.0)
        self.anim_dark.setEndValue(100.0)
        self.anim_info.setEndValue(255.0)
        self.panel_anim.setEndValue(QtCore.QPoint(10, 280))
        
        self.anim_scale.start()
        self.anim_dark.start()
        self.anim_info.start()
        self.panel_anim.start()

        if hasattr(self, 'more_btn_anim'):
            self.more_btn_anim.setEndValue(QtCore.QPoint(self.width() - 40, -40))
            self.more_btn_anim.start()
        
        self.shadow_effect.setOffset(0, 5)
        self.shadow_effect.setBlurRadius(15)
        super().leaveEvent(event)

    @safe_paint
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)

        rect = self.rect()
        
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(rect), 15, 15)
        painter.setClipPath(path)

        painter.save()
        scale_factor = max(rect.width() / self.pixmap.width(), rect.height() / self.pixmap.height())
        final_scale = scale_factor * self._hover_scale
        painter.translate(rect.center())
        painter.scale(final_scale, final_scale)
        painter.drawPixmap(-self.pixmap.width() // 2, -self.pixmap.height() // 2, self.pixmap)
        painter.restore()

        if self._darkness_alpha > 0:
            painter.fillRect(rect, QtGui.QColor(0, 0, 0, int(self._darkness_alpha)))

        if self._info_alpha > 0:
            gradient = QtGui.QLinearGradient(0, rect.height() * 0.4, 0, rect.height())
            gradient.setColorAt(0, QtGui.QColor(0, 0, 0, 0))
            gradient.setColorAt(1, QtGui.QColor(0, 0, 0, int(min(220, self._info_alpha))))
            painter.fillRect(rect, QtGui.QBrush(gradient))

            painter.setPen(QtGui.QColor(255, 255, 255, int(self._info_alpha)))
            font = QtGui.QFont("Inter Tight SemiBold", 13, QtGui.QFont.Weight.Bold)
            painter.setFont(font)
            
            text_rect = QtCore.QRect(15, rect.height() - 75, rect.width() - 45, 65)
            painter.drawText(
                text_rect, 
                QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignBottom | QtCore.Qt.TextFlag.TextWordWrap, 
                self.character_name
            )

            if hasattr(self, 'icon_api_pixmap') and not self.icon_api_pixmap.isNull():
                painter.setOpacity(self._info_alpha / 255.0)
                icon_rect = QtCore.QRect(rect.width() - 30, rect.height() - 30, 20, 20)
                painter.drawPixmap(icon_rect, self.icon_api_pixmap)
                painter.setOpacity(1.0)

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            import asyncio
            asyncio.create_task(self.open_chat(self.character_name)) 
        super().mousePressEvent(event)

class AnimatedHoverButton(QtWidgets.QPushButton):
    def __init__(self, icon_path, hover_color, tooltip_text, parent=None, base_color=None):
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.setToolTip(tooltip_text)
        
        self.setIcon(QtGui.QIcon(icon_path))
        self.setIconSize(QtCore.QSize(18, 18))

        if base_color:
            self._base_color = QtGui.QColor(base_color) if isinstance(base_color, (str, int)) else base_color
        else:
            self._base_color = QtGui.QColor(0, 0, 0, 0)
            
        self._hover_color = QtGui.QColor(hover_color) if isinstance(hover_color, (str, int)) else hover_color
        
        self._current_color = QtGui.QColor(self._base_color)

        self.anim = QtCore.QVariantAnimation(self)
        self.anim.setDuration(200)
        self.anim.valueChanged.connect(self._update_color)

        self.setStyleSheet("""
            QPushButton {
                background-color: transparent; 
                border: none;
            }
            QToolTip { 
                background-color: rgba(25, 25, 30, 0.95); 
                color: #E0E0E0; 
                border: 1px solid rgba(255, 255, 255, 0.15); 
                border-radius: 6px; 
                padding: 6px 10px; 
                font-size: 12px; 
                font-weight: 500; 
            }
        """)

    def _update_color(self, color):
        self._current_color = color
        self.update()

    def enterEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(self._current_color)
        self.anim.setEndValue(self._hover_color)
        self.anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(self._current_color)
        self.anim.setEndValue(self._base_color)
        self.anim.start()
        super().leaveEvent(event)

    @safe_paint
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        
        painter.setBrush(self._current_color)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawEllipse(self.rect())
        
        painter.end()
        super().paintEvent(event)

class AnimatedDotsWidget(QWidget):
    def __init__(self, color_hex, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 20)
        
        self.dot_color = QColor(color_hex)
        self.phase = 0.0
        
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(16)

    def update_animation(self):
        self.phase += 0.12
        self.update()

    @safe_paint
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        dot_radius = 3.5
        spacing = 12
        start_x = 2
        center_y = self.height() / 2

        for i in range(3):
            local_phase = self.phase - (i * 0.8)
            
            y_offset = math.sin(local_phase) * 4
            
            alpha_factor = (math.sin(local_phase) + 1) / 2
            alpha = int(80 + (175 * alpha_factor))
            
            color = QColor(self.dot_color)
            color.setAlpha(alpha)
            painter.setBrush(color)
            
            painter.drawEllipse(
                QtCore.QPointF(start_x + (i * spacing) + dot_radius, center_y + y_offset), 
                dot_radius, 
                dot_radius
            )

class TypingIndicatorWidget(QWidget):
    def __init__(self, character_name, avatar_path, s_appearance, margins, parent=None):
        super().__init__(parent)
        self.configuration_settings = configuration.ConfigurationSettings()

        self.translations = {}
        self.selected_language = self.configuration_settings.get_main_setting("program_language")
        self.load_translation("ru" if self.selected_language == 1 else "en")

        self.character_name = character_name
        
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(10, 5, 10, 5)
        self.main_layout.setSpacing(0)

        s = s_appearance
        op = s["bubble_opacity"]
        r = s["border_radius"]
        
        def get_rgba(hex_col, alpha):
            h = hex_col.lstrip("#")
            return f"rgba({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}, {alpha/100})"
            
        bg_color = get_rgba(s["char_bubble_color"], op)
        
        radius_css = f"border-top-right-radius: {r}px; border-bottom-right-radius: {r}px; border-top-left-radius: {r}px; border-bottom-left-radius: 0px;"

        self.bubble_frame = QFrame()
        self.bubble_frame.setObjectName("typing_bubble_frame")
        self.bubble_frame.setStyleSheet(f"""
            QFrame#typing_bubble_frame {{
                background-color: {bg_color};
                {radius_css}
                margin: 5px;
            }}
        """)
        self.bubble_frame.setFixedWidth(s.get("max_width", 750))

        self.bubble_layout = QVBoxLayout(self.bubble_frame)
        self.bubble_layout.setContentsMargins(14, 12, 14, 12)
        self.bubble_layout.setSpacing(8)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        raw_pixmap = QPixmap(avatar_path)
        if raw_pixmap.isNull():
            raw_pixmap = QPixmap("app/gui/icons/logotype.png")

        target_size = 64
        label_size = 26
        scaled_pixmap = raw_pixmap.scaled(target_size, target_size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        crop_x = (scaled_pixmap.width() - target_size) // 2
        crop_y = (scaled_pixmap.height() - target_size) // 2
        square_pixmap = scaled_pixmap.copy(crop_x, crop_y, target_size, target_size)

        final_avatar_pixmap = QPixmap(target_size, target_size)
        final_avatar_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(final_avatar_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        path = QtGui.QPainterPath()
        path.addEllipse(0, 0, target_size, target_size)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, square_pixmap)
        painter.end()

        self.avatar_label = QLabel()
        self.avatar_label.setPixmap(final_avatar_pixmap)
        self.avatar_label.setFixedSize(label_size, label_size)
        self.avatar_label.setScaledContents(True)
        self.avatar_label.setStyleSheet("background: transparent; border: none;")

        self.name_label = QLabel(self.character_name)
        name_font = QtGui.QFont("Inter Tight SemiBold")
        name_font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.name_label.setFont(name_font)
        self.name_label.setStyleSheet(f"""
            QLabel {{
                color: {s["text_color"]};
                font-size: {max(11, s["font_size"] - 2)}px;
                font-weight: bold;
                background: transparent;
                border: none;
            }}
        """)

        header_layout.addWidget(self.avatar_label)
        header_layout.addWidget(self.name_label)
        header_layout.addStretch()
        self.bubble_layout.addLayout(header_layout)

        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(5)

        self.animated_dots = AnimatedDotsWidget(s["text_color"])
        
        self.status_label = QLabel(self.translations.get("typingIndicator_text", "Thinking"))
        status_font = QtGui.QFont("Inter Tight Medium")
        status_font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.status_label.setFont(status_font)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {s["text_color"]};
                font-size: {s["font_size"] - 1}px;
                background: transparent;
                border: none;
                opacity: 0.6;
            }}
        """)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 2)
        self.animated_dots.setGraphicsEffect(shadow)

        status_layout.addWidget(self.animated_dots)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        
        self.bubble_layout.addLayout(status_layout)

        self.main_layout.addStretch()
        self.main_layout.addWidget(self.bubble_frame)
        self.main_layout.addStretch()

    def load_translation(self, language):
        file_path = f"app/translations/{language}.yaml"
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                self.translations = yaml.safe_load(file)
        else:
            self.translations = {}

class SmoothMessageFrame(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._target_height = -1.0
        self._current_height = -1.0
        
        self.anim_timer = QtCore.QTimer(self)
        self.anim_timer.setInterval(32)
        self.anim_timer.timeout.connect(self._anim_tick)
        
        self.scroll_callback = None
        self._last_height = -1

    def _anim_tick(self):
        if self._target_height < 0:
            self.anim_timer.stop()
            return

        diff = self._target_height - self._current_height

        if abs(diff) < 1.0:
            self._current_height = self._target_height
            new_h = round(self._current_height)
            self.setFixedHeight(new_h)
            self.anim_timer.stop()
            if self.scroll_callback:
                self.scroll_callback()
            self._last_height = new_h
            return

        self._current_height += diff * 0.6

        new_h = round(self._current_height)

        if new_h != self._last_height:
            self.setFixedHeight(new_h)
            self._last_height = new_h
            
            if self.scroll_callback:
                self.scroll_callback()

    def update_smooth_height(self):
        if not self.layout():
            return

        new_target = float(self.layout().sizeHint().height())

        if abs(new_target - self._current_height) < 3.0:
            return

        if new_target != self._target_height and new_target > self._current_height + 2:
            self._target_height = new_target
            if not self.anim_timer.isActive():
                self.anim_timer.start()

    def finalize_size(self):
        self.anim_timer.stop()
        
        if self._target_height > 0:
            final_h = round(self._target_height)
            self.setFixedHeight(final_h)
            self._last_height = final_h
        
        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)
        
        self._current_height = -1.0
        self._target_height = -1.0
        self._last_height = -1

class MethodCard(QFrame):
    clicked = QtCore.pyqtSignal()
    
    def __init__(self, title, description, icon_path, parent=None):
        super().__init__(parent)
        self.setFixedHeight(120)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.setStyleSheet("""
            MethodCard {
                background-color: #2B2B2B;
                border: 1px solid #3A3A3A;
                border-radius: 12px;
            }
            MethodCard:hover {
                background-color: #363636; 
                border: 1px solid #555555;
            }
            QLabel { border: none; background: transparent; }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(15)

        icon_label = QLabel()
        pixmap = QtGui.QPixmap(icon_path)
        if not pixmap.isNull():
            icon_label.setPixmap(pixmap.scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        icon_label.setFixedSize(36, 36)
        layout.addWidget(icon_label)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #E0E0E0; font-size: 15px; font-weight: bold;")
        title_lbl.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Maximum)
        
        desc_lbl = QLabel(description)
        desc_lbl.setStyleSheet("color: #A0A0A0; font-size: 11px; line-height: 1.2;")
        desc_lbl.setWordWrap(True)
        desc_lbl.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Maximum)
        
        text_layout.addWidget(title_lbl)
        text_layout.addWidget(desc_lbl)
        layout.addLayout(text_layout, 1)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

class SoulMemoryViewer(QtWidgets.QDialog):
    def __init__(self, character_name: str, memory_dir: Path, parent=None, 
                 subtitle_tr="...", 
                 content_view_tr="Select an entry to view its contents...", 
                 title_text_tr="Memory Archive",
                 tab_database_tr="Database",
                 tab_user_profile_tr="User Profile",
                 tab_diary_tr="Diary",
                 tab_logs_tr="Logs",
                 btn_save_tr="Save",
                 btn_delete_tr="Delete",
                 btn_refresh_tr="Refresh",
                 btn_open_folder_tr="Open Folder",
                 msg_save_success_tr="Saved",
                 msg_save_error_tr="Error",
                 msg_delete_confirm_title_tr="Confirm",
                 msg_delete_confirm_text_tr="Are you sure?",
                 msg_delete_success_tr="Deleted",
                 msg_delete_error_tr="Error",
                 msg_logs_empty_tr="No logs yet...",
                 btn_edit_tr="Edit",
                 btn_preview_tr="Preview"):
        
        super().__init__(parent)

        self.msg_save_success_tr = msg_save_success_tr
        self.msg_save_error_tr = msg_save_error_tr
        self.msg_delete_confirm_title_tr = msg_delete_confirm_title_tr
        self.msg_delete_confirm_text_tr = msg_delete_confirm_text_tr
        self.msg_delete_success_tr = msg_delete_success_tr
        self.msg_delete_error_tr = msg_delete_error_tr
        self.msg_logs_empty_tr = msg_logs_empty_tr

        self.setWindowTitle(f"Soul Memory — {character_name}")
        self.resize(950, 700)
        
        self.setStyleSheet("""
            QDialog { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0F0F13, stop:1 #1A1A24); 
                color: #E2E8F0; 
                font-family: 'Segoe UI Variable', 'Segoe UI', 'Inter', sans-serif;
            }
            QTabWidget::pane { border: none; background: transparent; padding-top: 10px; }
            QTabBar::tab { background: transparent; color: #64748B; padding: 10px 20px; font-size: 14px; font-weight: 600; border-bottom: 2px solid transparent; margin-right: 15px; }
            QTabBar::tab:hover { color: #CBD5E1; }
            QTabBar::tab:selected { color: #60A5FA; border-bottom: 2px solid #60A5FA; }
            QListWidget { background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 8px; outline: none; }
            QListWidget::item { padding: 12px; border-radius: 8px; margin-bottom: 4px; color: #CBD5E1; }
            QListWidget::item:selected { background: rgba(96, 165, 250, 0.15); color: #FFFFFF; border: 1px solid rgba(96, 165, 250, 0.3); }
            QListWidget::item:hover:!selected { background: rgba(255, 255, 255, 0.04); }
            QTextEdit, QPlainTextEdit { background: rgba(10, 10, 15, 0.5); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 12px; padding: 16px; color: #E2E8F0; font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 13px; selection-background-color: rgba(96, 165, 250, 0.4); }
            QTextEdit:focus, QPlainTextEdit:focus { border: 1px solid rgba(96, 165, 250, 0.4); background: rgba(15, 15, 20, 0.7); }
            
            QPushButton { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 8px 18px; color: #E2E8F0; font-weight: 600; font-size: 13px; }
            QPushButton:hover { background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); }
            QPushButton:pressed { background: rgba(255, 255, 255, 0.03); }
            
            QPushButton#saveBtn { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(46, 160, 67, 0.8), stop:1 rgba(35, 134, 54, 0.8)); border: 1px solid rgba(255, 255, 255, 0.15); }
            QPushButton#saveBtn:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(56, 180, 77, 0.9), stop:1 rgba(45, 154, 64, 0.9)); }
            QPushButton#saveBtn:disabled { background: rgba(255, 255, 255, 0.02); color: rgba(255, 255, 255, 0.15); border: 1px solid rgba(255, 255, 255, 0.03); }

            QPushButton#previewBtn { background: rgba(96, 165, 250, 0.1); border: 1px solid rgba(96, 165, 250, 0.3); color: #60A5FA; }
            QPushButton#previewBtn:hover { background: rgba(96, 165, 250, 0.2); border: 1px solid rgba(96, 165, 250, 0.5); color: #FFFFFF; }
            QPushButton#previewBtn:pressed { background: rgba(96, 165, 250, 0.05); }

            QPushButton#deleteBtn { background: rgba(220, 53, 69, 0.15); border: 1px solid rgba(220, 53, 69, 0.3); color: #FCA5A5; }
            QPushButton#deleteBtn:hover { background: rgba(220, 53, 69, 0.3); border: 1px solid rgba(220, 53, 69, 0.5); color: #FFF; }
            QPushButton#deleteBtn:disabled { background: rgba(255,255,255,0.05); color: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.05); }

            QSplitter::handle { background: transparent; width: 6px; }
            QScrollBar:vertical { border: none; background: transparent; width: 8px; margin: 2px 0 2px 0; }
            QScrollBar::handle:vertical { background: rgba(255, 255, 255, 0.15); min-height: 30px; border-radius: 4px; }
            QScrollBar::handle:vertical:hover { background: rgba(255, 255, 255, 0.3); }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)

        self.memory_dir = memory_dir
        self.index_path = self.memory_dir / "MEMORY.md"
        self.usr_path = self.memory_dir / "USER.md"
        self.topics_dir = self.memory_dir / "topics"
        self.log_path = self.memory_dir / "agent_logs.txt"

        self.btn_edit_tr = btn_edit_tr
        self.btn_preview_tr = btn_preview_tr
        
        self.db_current_file_path = None
        self.diary_current_file_path = None

        self.db_preview_active = True
        self.user_preview_active = True
        self.diary_preview_active = True

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # === HEADER ===
        header_layout = QtWidgets.QVBoxLayout()
        header_layout.setSpacing(4)
        title = QtWidgets.QLabel(f"{title_text_tr}: {character_name}")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #FFFFFF;")
        subtitle = QtWidgets.QLabel(subtitle_tr)
        subtitle.setStyleSheet("color: #94A3B8; font-size: 13px;")
        subtitle.setWordWrap(True)
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_layout.addLayout(header_layout)

        self.tabs = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tabs)

        # === TAB 1: DATABASE ===
        self.tab_database = QtWidgets.QWidget()
        db_layout = QtWidgets.QVBoxLayout(self.tab_database)
        db_layout.setContentsMargins(0, 5, 0, 0)
        
        splitter_db = QtWidgets.QSplitter(Qt.Orientation.Horizontal)
        
        self.topic_list = QtWidgets.QListWidget()
        self.topic_list.setFixedWidth(240)
        
        db_edit_container = QtWidgets.QWidget()
        db_edit_layout = QtWidgets.QVBoxLayout(db_edit_container)
        db_edit_layout.setContentsMargins(0, 0, 0, 0)
        db_edit_layout.setSpacing(12)
        
        self.db_content_view = QtWidgets.QTextEdit()
        self.db_content_view.setPlaceholderText(content_view_tr)
        self._apply_shadow(self.db_content_view)
        
        db_btn_layout = QtWidgets.QHBoxLayout()
        self.btn_db_save = QtWidgets.QPushButton(btn_save_tr)
        self.btn_db_save.setObjectName("saveBtn")
        self.btn_db_save.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_db_preview = QtWidgets.QPushButton(btn_edit_tr)
        self.btn_db_preview.setObjectName("previewBtn")
        self.btn_db_preview.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_db_delete = QtWidgets.QPushButton(btn_delete_tr)
        self.btn_db_delete.setObjectName("deleteBtn")
        self.btn_db_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.label_db_status = QtWidgets.QLabel("")
        self.label_db_status.setStyleSheet("color: #4ADE80; font-weight: 600; font-size: 13px;")
        
        db_btn_layout.addWidget(self.btn_db_save)
        db_btn_layout.addWidget(self.btn_db_preview)
        db_btn_layout.addWidget(self.btn_db_delete)
        db_btn_layout.addWidget(self.label_db_status)
        db_btn_layout.addStretch()
        
        db_edit_layout.addWidget(self.db_content_view)
        db_edit_layout.addLayout(db_btn_layout)

        splitter_db.addWidget(self.topic_list)
        splitter_db.addWidget(db_edit_container)
        splitter_db.setStretchFactor(1, 1)
        db_layout.addWidget(splitter_db)

        # === TAB 2: USER PROFILE ===
        self.tab_user = QtWidgets.QWidget()
        user_layout = QtWidgets.QVBoxLayout(self.tab_user)
        user_layout.setContentsMargins(0, 5, 0, 0)
        user_layout.setSpacing(12)

        self.user_content_view = QtWidgets.QTextEdit()
        self.user_content_view.setPlaceholderText("User profile and dynamic relationship data...")
        self.user_content_view.setStyleSheet("font-family: 'Segoe UI', 'Inter', sans-serif; font-size: 14px; line-height: 1.5;")
        self._apply_shadow(self.user_content_view)

        user_btn_layout = QtWidgets.QHBoxLayout()
        self.btn_user_save = QtWidgets.QPushButton(btn_save_tr)
        self.btn_user_save.setObjectName("saveBtn")
        self.btn_user_save.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_user_preview = QtWidgets.QPushButton(btn_edit_tr)
        self.btn_user_preview.setObjectName("previewBtn")
        self.btn_user_preview.setCursor(Qt.CursorShape.PointingHandCursor)

        self.label_user_status = QtWidgets.QLabel("")
        self.label_user_status.setStyleSheet("color: #4ADE80; font-weight: 600; font-size: 13px;")

        user_btn_layout.addWidget(self.btn_user_save)
        user_btn_layout.addWidget(self.btn_user_preview)
        user_btn_layout.addWidget(self.label_user_status)
        user_btn_layout.addStretch()

        user_layout.addWidget(self.user_content_view)
        user_layout.addLayout(user_btn_layout)

        # === TAB 3: DIARY ===
        self.tab_diary = QtWidgets.QWidget()
        diary_layout = QtWidgets.QVBoxLayout(self.tab_diary)
        diary_layout.setContentsMargins(0, 5, 0, 0)
        
        splitter_diary = QtWidgets.QSplitter(Qt.Orientation.Horizontal)
        
        self.diary_list = QtWidgets.QListWidget()
        self.diary_list.setFixedWidth(240)
        
        diary_edit_container = QtWidgets.QWidget()
        diary_edit_layout = QtWidgets.QVBoxLayout(diary_edit_container)
        diary_edit_layout.setContentsMargins(0, 0, 0, 0)
        diary_edit_layout.setSpacing(12)
        
        self.diary_content_view = QtWidgets.QTextEdit()
        self.diary_content_view.setPlaceholderText("Select a diary entry to read her thoughts...")
        self.diary_content_view.setStyleSheet("font-family: 'Segoe UI', 'Inter', sans-serif; font-size: 14px; line-height: 1.5;")
        self._apply_shadow(self.diary_content_view)
        
        diary_btn_layout = QtWidgets.QHBoxLayout()
        self.btn_diary_save = QtWidgets.QPushButton(btn_save_tr)
        self.btn_diary_save.setObjectName("saveBtn")
        self.btn_diary_save.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_diary_preview = QtWidgets.QPushButton(btn_edit_tr)
        self.btn_diary_preview.setObjectName("previewBtn")
        self.btn_diary_preview.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_diary_delete = QtWidgets.QPushButton(btn_delete_tr)
        self.btn_diary_delete.setObjectName("deleteBtn")
        self.btn_diary_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.label_diary_status = QtWidgets.QLabel("")
        self.label_diary_status.setStyleSheet("color: #4ADE80; font-weight: 600; font-size: 13px;")
        
        diary_btn_layout.addWidget(self.btn_diary_save)
        diary_btn_layout.addWidget(self.btn_diary_preview)
        diary_btn_layout.addWidget(self.btn_diary_delete)
        diary_btn_layout.addWidget(self.label_diary_status)
        diary_btn_layout.addStretch()
        
        diary_edit_layout.addWidget(self.diary_content_view)
        diary_edit_layout.addLayout(diary_btn_layout)

        splitter_diary.addWidget(self.diary_list)
        splitter_diary.addWidget(diary_edit_container)
        splitter_diary.setStretchFactor(1, 1)
        diary_layout.addWidget(splitter_diary)

        # === TAB 4: LOGS ===
        self.tab_logs = QtWidgets.QWidget()
        logs_layout = QtWidgets.QVBoxLayout(self.tab_logs)
        logs_layout.setContentsMargins(0, 5, 0, 0)
        self.logs_view = QtWidgets.QPlainTextEdit()
        self.logs_view.setReadOnly(True)
        self.logs_view.setPlaceholderText(self.msg_logs_empty_tr)
        self.logs_view.setStyleSheet("color: #A3BE8C;")
        logs_layout.addWidget(self.logs_view)

        self.tabs.addTab(self.tab_database, tab_database_tr)
        self.tabs.addTab(self.tab_user, tab_user_profile_tr)
        self.tabs.addTab(self.tab_diary, tab_diary_tr)
        self.tabs.addTab(self.tab_logs, tab_logs_tr)

        bottom_layout = QtWidgets.QHBoxLayout()
        self.btn_refresh = QtWidgets.QPushButton(btn_refresh_tr)
        self.btn_refresh.setIcon(QtGui.QIcon("app/gui/icons/reload.png"))
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_open_folder = QtWidgets.QPushButton(btn_open_folder_tr)
        self.btn_open_folder.setIcon(QtGui.QIcon("app/gui/icons/folder.png"))
        self.btn_open_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        
        bottom_layout.addWidget(self.btn_refresh)
        bottom_layout.addWidget(self.btn_open_folder)
        bottom_layout.addStretch()
        main_layout.addLayout(bottom_layout)

        self.btn_refresh.clicked.connect(self.refresh_memory)
        self.btn_open_folder.clicked.connect(self._open_memory_folder)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        self.topic_list.currentRowChanged.connect(self.load_db_content)
        self.btn_db_save.clicked.connect(lambda: self.save_file(self.db_current_file_path, self.db_content_view, self.label_db_status))
        self.btn_db_preview.clicked.connect(self.toggle_db_preview)
        self.btn_db_delete.clicked.connect(lambda: self.delete_file(self.db_current_file_path, self.label_db_status))
        
        self.btn_user_save.clicked.connect(lambda: self.save_file(self.usr_path, self.user_content_view, self.label_user_status))
        self.btn_user_preview.clicked.connect(self.toggle_user_preview)

        self.diary_list.currentRowChanged.connect(self.load_diary_content)
        self.btn_diary_save.clicked.connect(lambda: self.save_file(self.diary_current_file_path, self.diary_content_view, self.label_diary_status))
        self.btn_diary_preview.clicked.connect(self.toggle_diary_preview)
        self.btn_diary_delete.clicked.connect(lambda: self.delete_file(self.diary_current_file_path, self.label_diary_status))

        self.refresh_memory()

    def _apply_shadow(self, widget):
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QtGui.QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        widget.setGraphicsEffect(shadow)

    def toggle_db_preview(self):
        if not self.db_current_file_path or not self.db_current_file_path.exists():
            return
        self.db_preview_active = not self.db_preview_active
        self.load_db_content(self.topic_list.currentRow())

    def toggle_user_preview(self):
        self.user_preview_active = not self.user_preview_active
        self.load_user_profile_content()

    def toggle_diary_preview(self):
        if not self.diary_current_file_path or not self.diary_current_file_path.exists():
            return
        self.diary_preview_active = not self.diary_preview_active
        self.load_diary_content(self.diary_list.currentRow())

    def load_user_profile_content(self):
        self.label_user_status.setText("")
        if self.usr_path.exists():
            try:
                text = self.usr_path.read_text(encoding="utf-8")
                if self.user_preview_active:
                    self.user_content_view.setMarkdown(text)
                    self.user_content_view.setReadOnly(True)
                    self.btn_user_save.setEnabled(False)
                    self.btn_user_preview.setText(self.btn_edit_tr)
                else:
                    self.user_content_view.setPlainText(text)
                    self.user_content_view.setReadOnly(False)
                    self.btn_user_save.setEnabled(True)
                    self.btn_user_preview.setText(self.btn_preview_tr)
            except Exception as e:
                self.user_content_view.setPlainText(f"Error reading USER.md: {e}")
        else:
            self.user_content_view.setPlainText("")

    def refresh_memory(self):
        self.label_db_status.setText("")
        self.label_user_status.setText("")
        self.label_diary_status.setText("")
        self.topic_list.clear()
        self.diary_list.clear()
        
        item = QtWidgets.QListWidgetItem("📄 MEMORY.md (Core Index)")
        item.setData(Qt.ItemDataRole.UserRole, str(self.index_path))
        self.topic_list.addItem(item)
        
        self.load_user_profile_content()
        
        if self.topics_dir.exists():
            files = sorted(self.topics_dir.iterdir(), reverse=True)
            for f in files:
                if f.suffix == ".md":
                    if f.name.lower().startswith("diary_"):
                        display_name = f.stem.replace("diary_", "").replace("Diary_", "")
                        d_item = QtWidgets.QListWidgetItem(f"📓 {display_name}")
                        d_item.setData(Qt.ItemDataRole.UserRole, str(f))
                        self.diary_list.addItem(d_item)
                    else:
                        display_name = f"🗂️ {f.stem.replace('_', ' ').title()}"
                        t_item = QtWidgets.QListWidgetItem(display_name)
                        t_item.setData(Qt.ItemDataRole.UserRole, str(f))
                        self.topic_list.addItem(t_item)
        
        if self.topic_list.count() > 0: self.topic_list.setCurrentRow(0)
        if self.diary_list.count() > 0: self.diary_list.setCurrentRow(0)

        self.load_agent_logs()

    def load_db_content(self, index):
        self.label_db_status.setText("")
        if index < 0: return
        
        item = self.topic_list.item(index)
        _, idx_path, *_ = self.get_memory_paths_safe()
        file_path = Path(item.data(Qt.ItemDataRole.UserRole))
        self.db_current_file_path = file_path
        
        if file_path.exists():
            text = file_path.read_text(encoding="utf-8")
            if self.db_preview_active:
                self.db_content_view.setMarkdown(text)
                self.db_content_view.setReadOnly(True)
                self.btn_db_save.setEnabled(False)
                self.btn_db_preview.setText(self.btn_edit_tr)
            else:
                self.db_content_view.setPlainText(text)
                self.db_content_view.setReadOnly(False)
                self.btn_db_save.setEnabled(True)
                self.btn_db_preview.setText(self.btn_preview_tr)
        else:
            self.db_content_view.setPlainText("")
            
        self.btn_db_delete.setEnabled(file_path.name != "MEMORY.md")

    def get_memory_paths_safe(self) -> tuple:
        safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in self.windowTitle().split("—")[-1]).strip()
        mem_dir = self.memory_dir
        return mem_dir, self.index_path, self.usr_path, self.topics_dir, self.log_path, mem_dir / "backups"

    def load_diary_content(self, index):
        self.label_diary_status.setText("")
        if index < 0: return
        
        item = self.diary_list.item(index)
        file_path = Path(item.data(Qt.ItemDataRole.UserRole))
        self.diary_current_file_path = file_path
        
        if file_path.exists():
            text = file_path.read_text(encoding="utf-8")
            if self.diary_preview_active:
                self.diary_content_view.setMarkdown(text)
                self.diary_content_view.setReadOnly(True)
                self.btn_diary_save.setEnabled(False)
                self.btn_diary_preview.setText(self.btn_edit_tr)
            else:
                self.diary_content_view.setPlainText(text)
                self.diary_content_view.setReadOnly(False)
                self.btn_diary_save.setEnabled(True)
                self.btn_diary_preview.setText(self.btn_preview_tr)
        else:
            self.diary_content_view.setPlainText("")
            
        self.btn_diary_delete.setEnabled(True)

    def save_file(self, file_path, text_widget, status_label):
        if file_path:
            try:
                new_content = text_widget.toPlainText()
                file_path.write_text(new_content, encoding="utf-8")
                status_label.setStyleSheet("color: #4ADE80;")
                status_label.setText(self.msg_save_success_tr)
                QtCore.QTimer.singleShot(2500, lambda: status_label.setText(""))
            except Exception as e:
                status_label.setStyleSheet("color: #F87171;")
                status_label.setText(f"{self.msg_save_error_tr}: {e}")

    def delete_file(self, file_path, status_label):
        if file_path and file_path.name != "MEMORY.md":
            dialog = SowConfirmDialog(
                parent=self,
                title=self.msg_delete_confirm_title_tr,
                text=f"{self.msg_delete_confirm_text_tr} ('{file_path.name}')?",
                confirm_text="Delete",
                danger=True
            )
            
            if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                try:
                    os.remove(file_path)
                    
                    status_label.setStyleSheet("color: #FCA5A5;")
                    status_label.setText(self.msg_delete_success_tr)
                    QtCore.QTimer.singleShot(2500, lambda: status_label.setText(""))
                    
                    self.refresh_memory()
                except Exception as e:
                    status_label.setStyleSheet("color: #F87171;")
                    status_label.setText(f"{self.msg_delete_error_tr}: {e}")
    
    def load_agent_logs(self):
        if self.log_path.exists():
            try:
                self.logs_view.setPlainText(self.log_path.read_text(encoding="utf-8"))
                self.logs_view.verticalScrollBar().setValue(self.logs_view.verticalScrollBar().maximum())
            except Exception as e:
                self.logs_view.setPlainText(f"Error reading logs: {e}")
        else:
            self.logs_view.setPlainText(self.msg_logs_empty_tr)

    def _open_memory_folder(self):
        import sys
        folder = str(self.memory_dir.absolute())
        try:
            if os.name == "nt":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as e:
            logger.error(f"Failed to open memory folder '{folder}': {e}")

    def on_tab_changed(self, index):
        if index == 1:
            self.load_user_profile_content()
        elif index == 2:
            if self.diary_list.currentRow() >= 0:
                self.load_diary_content(self.diary_list.currentRow())
        elif index == 3:
            self.load_agent_logs()

class CharacterFolderCard(QtWidgets.QFrame):
    def __init__(self, group_name: str, char_count: int, preview_avatars: list, main_app, parent=None):
        super().__init__(parent)
        self.setFixedSize(210, 270)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

        self.translations = _load_translations()
        
        self.group_name = group_name
        self.char_count = char_count
        self.main_app = main_app
        
        self.pixmap = QtGui.QPixmap(210, 270)
        self.pixmap.fill(QtCore.Qt.GlobalColor.transparent)
        
        painter = QtGui.QPainter(self.pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        
        if preview_avatars:
            positions =[
                QtCore.QRectF(0, 0, 105, 135), QtCore.QRectF(105, 0, 105, 135),
                QtCore.QRectF(0, 135, 105, 135), QtCore.QRectF(105, 135, 105, 135)
            ]
            for i, path in enumerate(preview_avatars[:4]):
                px = QtGui.QPixmap(path)
                if px.isNull(): px = QtGui.QPixmap("app/gui/icons/logotype.png")
                
                scaled = px.scaled(105, 135, QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding, QtCore.Qt.TransformationMode.SmoothTransformation)
                sx = (scaled.width() - 105) // 2
                sy = (scaled.height() - 135) // 2
                cropped = scaled.copy(sx, sy, 105, 135)
                painter.drawPixmap(int(positions[i].x()), int(positions[i].y()), cropped)
            
            painter.fillRect(self.pixmap.rect(), QtGui.QColor(0, 0, 0, 100))
        else:
            gradient = QtGui.QLinearGradient(0, 0, 210, 270)
            gradient.setColorAt(0, QtGui.QColor(35, 35, 50))
            gradient.setColorAt(1, QtGui.QColor(20, 20, 35))
            painter.fillRect(self.pixmap.rect(), QtGui.QBrush(gradient))
            
            folder_icon = QtGui.QPixmap("app/gui/icons/folder.png").scaled(52, 52, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap(210//2 - 26, 270//2 - 40, folder_icon)
            
        painter.end()

        self.shadow_effect = QtWidgets.QGraphicsDropShadowEffect(self)
        self.shadow_effect.setBlurRadius(15)
        self.shadow_effect.setColor(QtGui.QColor(0, 0, 0, 100))
        self.shadow_effect.setOffset(0, 5)
        self.setGraphicsEffect(self.shadow_effect)

        self._hover_scale = 1.0
        self.anim_scale = QtCore.QPropertyAnimation(self, b"hover_scale")
        self.anim_scale.setDuration(350)
        self.anim_scale.setEasingCurve(QtCore.QEasingCurve.Type.InOutCubic)

        self._darkness_alpha = 100.0
        self.anim_dark = QtCore.QPropertyAnimation(self, b"darkness_alpha")
        self.anim_dark.setDuration(350)
        self.anim_dark.setEasingCurve(QtCore.QEasingCurve.Type.InOutCubic)

        self._info_alpha = 255.0
        self.anim_info = QtCore.QPropertyAnimation(self, b"info_alpha")
        self.anim_info.setDuration(300)
        self.anim_info.setEasingCurve(QtCore.QEasingCurve.Type.InOutCubic)

        self.action_panel = QtWidgets.QFrame(self)
        self.action_panel.setStyleSheet("background-color: rgba(15, 15, 15, 0.9); border-radius: 15px;")
        self.action_panel.setGeometry(10, 280, 190, 45)
        self.action_panel_layout = QtWidgets.QHBoxLayout(self.action_panel)
        self.action_panel_layout.setContentsMargins(5, 0, 5, 0)
        self.action_panel_layout.setSpacing(5)
        
        self.panel_anim = QtCore.QPropertyAnimation(self.action_panel, b"pos")
        self.panel_anim.setDuration(350)
        self.panel_anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        
        self.edit_btn = AnimatedHoverButton("app/gui/icons/more.png", "#1976D2", "Edit Folder")
        self.delete_btn = AnimatedHoverButton("app/gui/icons/bin.png", "#D32F2F", "Delete Folder")
        
        self.edit_btn.clicked.connect(self._on_edit_clicked)
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        
        self.action_panel_layout.addWidget(self.edit_btn)
        self.action_panel_layout.addWidget(self.delete_btn)

    @QtCore.pyqtProperty(float)
    def hover_scale(self): return self._hover_scale
    @hover_scale.setter
    def hover_scale(self, value): self._hover_scale = value; self.update()

    @QtCore.pyqtProperty(float)
    def darkness_alpha(self): return self._darkness_alpha
    @darkness_alpha.setter
    def darkness_alpha(self, value): self._darkness_alpha = value; self.update()

    @QtCore.pyqtProperty(float)
    def info_alpha(self): return self._info_alpha
    @info_alpha.setter
    def info_alpha(self, value): self._info_alpha = value; self.update()

    def enterEvent(self, event):
        self.anim_scale.setEndValue(1.05)
        self.anim_dark.setEndValue(0.0)
        self.anim_info.setEndValue(0.0)
        self.panel_anim.setEndValue(QtCore.QPoint(10, 215))
        
        self.anim_scale.start()
        self.anim_dark.start()
        self.anim_info.start()
        self.panel_anim.start()

        self.shadow_effect.setOffset(0, 8)
        self.shadow_effect.setBlurRadius(25)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim_scale.setEndValue(1.0)
        self.anim_dark.setEndValue(100.0)
        self.anim_info.setEndValue(255.0)
        self.panel_anim.setEndValue(QtCore.QPoint(10, 280))
        
        self.anim_scale.start()
        self.anim_dark.start()
        self.anim_info.start()
        self.panel_anim.start()

        self.shadow_effect.setOffset(0, 5)
        self.shadow_effect.setBlurRadius(15)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.main_app._open_folder_view(self.group_name)
        super().mousePressEvent(event)

    def _on_edit_clicked(self):
        self.main_app._open_folder_editor(self.group_name)

    def _on_delete_clicked(self):
        title = self.translations.get("folder_delete_confirm_title", "Delete Folder")
        msg = self.translations.get("folder_delete_confirm_msg", "Delete this folder?")
        detail = f"'{self.group_name}' · " + self.translations.get("folder_delete_detail", "Characters will return to the main list.")
        
        full_text = f"{msg}<br><span style='color: rgba(255,255,255,0.4); font-size: 9pt;'>{detail}</span>"

        dlg = SowConfirmDialog(
            parent=self.window(),
            title=title,
            text=full_text,
            confirm_text=self.translations.get("delete", "Delete"),
            danger=True
        )

        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            groups = self.main_app._get_groups()
            groups.pop(self.group_name, None)
            self.main_app._save_groups(groups)
            asyncio.create_task(self.main_app.set_main_tab())

    @safe_paint
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)

        rect = self.rect()
        
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(rect), 15, 15)
        painter.setClipPath(path)

        painter.save()
        scale_factor = max(rect.width() / self.pixmap.width(), rect.height() / self.pixmap.height())
        final_scale = scale_factor * self._hover_scale
        painter.translate(rect.center())
        painter.scale(final_scale, final_scale)
        painter.drawPixmap(-self.pixmap.width() // 2, -self.pixmap.height() // 2, self.pixmap)
        painter.restore()

        if self._darkness_alpha > 0:
            painter.fillRect(rect, QtGui.QColor(0, 0, 0, int(self._darkness_alpha)))

        if self._info_alpha > 0:
            gradient = QtGui.QLinearGradient(0, rect.height() * 0.4, 0, rect.height())
            gradient.setColorAt(0, QtGui.QColor(0, 0, 0, 0))
            gradient.setColorAt(1, QtGui.QColor(0, 0, 0, int(min(220, self._info_alpha))))
            painter.fillRect(rect, QtGui.QBrush(gradient))

            painter.setPen(QtGui.QColor(255, 255, 255, int(self._info_alpha)))
            
            font = QtGui.QFont("Inter Tight SemiBold", 13, QtGui.QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(QtCore.QRect(15, rect.height() - 75, rect.width() - 30, 30), 
                             QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter, 
                             self.group_name)
            
            character_count_label = self.main_app.translations.get("folder_characters_label", "characters")
            count_font = QtGui.QFont("Inter Tight Medium", 10)
            painter.setFont(count_font)
            painter.setPen(QtGui.QColor(255, 255, 255, int(self._info_alpha * 0.7)))
            count_text = f"{self.char_count} {character_count_label}"
            painter.drawText(QtCore.QRect(15, rect.height() - 45, rect.width() - 30, 20), 
                             QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter, 
                             count_text)

        painter.end()

class EditorCharacterItemWidget(QWidget):
    def __init__(self, avatar_path, parent=None):
        super().__init__(parent)
        self.setFixedSize(56, 56)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        avatar_label = QLabel()
        avatar_label.setFixedSize(52, 52)
        avatar_label.setStyleSheet("background: transparent; border: none;")
        
        if avatar_path and os.path.exists(avatar_path):
            pixmap = QtGui.QPixmap(avatar_path)
        else:
            pixmap = QtGui.QPixmap("app/gui/icons/person.png")
            
        if not pixmap.isNull():
            scaled = pixmap.scaled(52, 52, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            crop_x = (scaled.width() - 52) // 2
            crop_y = (scaled.height() - 52) // 2
            square = scaled.copy(crop_x, crop_y, 52, 52)
            
            final_px = QtGui.QPixmap(52, 52)
            final_px.fill(Qt.GlobalColor.transparent)
            painter = QtGui.QPainter(final_px)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)
            path = QtGui.QPainterPath()
            path.addEllipse(0, 0, 52, 52)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, square)
            painter.end()
            
            avatar_label.setPixmap(final_px)
            
        layout.addWidget(avatar_label)

class _GlowPanel(QtWidgets.QFrame):
    @safe_paint
    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        r = self.rect()
        rf = QtCore.QRectF(r)

        clip_path = QtGui.QPainterPath()
        clip_path.addRoundedRect(rf.adjusted(0, 0, 20, 0), 18, 18)
        p.setClipPath(clip_path)

        p.fillRect(r, QtGui.QColor(10, 9, 15))

        cx = rf.width() / 2

        bloom = QtGui.QRadialGradient(cx, rf.height() + 10, 130)
        bloom.setColorAt(0.00, QtGui.QColor(55, 130, 220, 40))
        bloom.setColorAt(1.00, QtGui.QColor(0, 0, 0, 0))
        p.fillRect(r, bloom)

        p.end()
        super().paintEvent(event)

_ACCENT        = "rgba(85, 155, 255, 1)"
_ACCENT_HOVER  = "rgba(120, 180, 255, 1)"
_ACCENT_BG     = "rgba(85, 155, 255, 0.10)"
_ACCENT_BG_H   = "rgba(85, 155, 255, 0.20)"
_ACCENT_BORDER = "rgba(85, 155, 255, 0.22)"
_ACCENT_BORDER_H = "rgba(85, 155, 255, 0.42)"

_QSS = f"""
    QFrame#MainFrame {{
        background-color: #0f0f15;
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 18px;
    }}

    QLabel {{
        color: rgba(255, 255, 255, 0.65);
        border: none;
        background: transparent;
        font-size: 11pt;
    }}

    QLabel#title_label {{
        font-size: 25pt;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: 0.4px;
    }}

    QLabel#version_badge {{
        font-size: 8.5pt;
        font-weight: 700;
        color: {_ACCENT};
        background-color: {_ACCENT_BG};
        border: 1px solid {_ACCENT_BORDER};
        padding: 2px 10px;
        border-radius: 9px;
        letter-spacing: 0.5px;
    }}

    QLabel#tagline_label {{
        font-size: 8pt;
        letter-spacing: 2.8px;
        color: rgba(255, 255, 255, 0.20);
        font-weight: 600;
    }}

    QPushButton#close_x_btn {{
        background-color: rgba(255, 255, 255, 0.04);
        color: rgba(255, 255, 255, 0.32);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 14px;
        font-size: 15pt;
        font-weight: 300;
        padding: 0px 0px 3px 0px
    }}
    QPushButton#close_x_btn:hover {{
        background-color: rgba(85, 155, 255, 0.20);
        border: 1px solid rgba(85, 155, 255, 0.32);
        color: rgba(160, 200, 255, 0.95);
    }}
    QPushButton#close_x_btn:pressed {{
        background-color: rgba(85, 155, 255, 0.30);
    }}

    QPushButton {{
        background-color: rgba(255, 255, 255, 0.04);
        color: rgba(255, 255, 255, 0.60);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 9px;
        padding: 0px 18px;
        font-size: 10pt;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: rgba(255, 255, 255, 0.09);
        border: 1px solid rgba(255, 255, 255, 0.17);
        color: #ffffff;
    }}
    QPushButton:pressed {{
        background-color: rgba(255, 255, 255, 0.13);
    }}

    QPushButton#donate_btn {{
        background-color: {_ACCENT_BG};
        color: {_ACCENT};
        border: 1px solid {_ACCENT_BORDER};
    }}
    QPushButton#donate_btn:hover {{
        background-color: {_ACCENT_BG_H};
        border: 1px solid {_ACCENT_BORDER_H};
        color: {_ACCENT_HOVER};
    }}
    QPushButton#donate_btn:pressed {{
        background-color: rgba(85, 155, 255, 0.28);
    }}

    QLabel#footer_text {{
        font-size: 9pt;
        color: rgba(255, 255, 255, 0.27);
    }}
    QLabel#footer_text a {{
        color: rgba(255, 255, 255, 0.45);
        text-decoration: none;
    }}
    QLabel#footer_text a:hover {{
        color: {_ACCENT_HOVER};
    }}

    QScrollArea {{ background: transparent; border: none; }}
    QWidget      {{ background: transparent; }}
    QScrollBar:vertical {{
        border: none;
        background: transparent;
        background-color: transparent;
        width: 4px;
        margin: 0px;
        border-radius: 2px;
    }}
    QScrollBar::handle:vertical {{
        background-color: rgba(255, 255, 255, 0.10);
        min-height: 28px;
        border-radius: 2px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {_ACCENT_BORDER_H};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical  {{ background: none; }}
"""

def _make_h_separator() -> QtWidgets.QFrame:
    sep = QtWidgets.QFrame()
    sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    sep.setStyleSheet("background-color: rgba(255,255,255,0.05); max-height: 1px; min-height: 1px; border: none;")
    return sep

def _make_v_separator() -> QtWidgets.QFrame:
    sep = QtWidgets.QFrame()
    sep.setFrameShape(QtWidgets.QFrame.Shape.VLine)
    sep.setStyleSheet("background-color: rgba(255,255,255,0.05); max-width: 1px; min-width: 1px; border: none;")
    return sep

def _open_url(url: str):
    QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

class AboutDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, translations=None):
        super().__init__(parent)
        self.translations = translations or {}
        self._drag_pos: QtCore.QPoint | None = None
        self._setup_ui()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event):
        if self._drag_pos and (event.buttons() & Qt.MouseButton.LeftButton):
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def _setup_ui(self):
        t = self.translations

        self.setWindowTitle(t.get("about_program_title", "About Soul of Waifu"))
        self.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(950, 650)

        font = QtGui.QFont("Inter Tight Medium")
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.setFont(font)
        
        dark_override = """
            QFrame#MainFrame {
                background-color: #0c0c0e;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
            }
            QWidget#LeftPanel {
                background-color: #08080a;
                border-top-left-radius: 12px;
                border-bottom-left-radius: 12px;
                border-right: 1px solid rgba(255, 255, 255, 0.04);
            }
        """
        self.setStyleSheet(_QSS + dark_override)

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)

        main_frame = QtWidgets.QFrame()
        main_frame.setObjectName("MainFrame")

        frame_layout = QtWidgets.QHBoxLayout(main_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        left_panel = _GlowPanel()
        left_panel.setObjectName("LeftPanel")
        left_panel.setFixedWidth(230)

        lp = QtWidgets.QVBoxLayout(left_panel)
        lp.setContentsMargins(24, 38, 24, 26)
        lp.setSpacing(0)
        lp.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        logo_lbl = QtWidgets.QLabel()
        logo_lbl.setObjectName("logo_label")
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_lbl.setFixedSize(160, 160)

        px = QtGui.QPixmap("app/gui/icons/logotype.ico")
        if not px.isNull():
            px = px.scaled(
                160, 160,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            logo_lbl.setPixmap(px)
        else:
            logo_lbl.setText("Soul of Waifu")
            logo_lbl.setStyleSheet(
                "font-size: 46pt; color: rgba(255,255,255,0.4);"
                "border: 1px solid rgba(255,255,255,0.1);"
                "border-radius: 70px;"
            )

        lp.addWidget(logo_lbl, 0, Qt.AlignmentFlag.AlignHCenter)

        lp.addSpacing(20)

        lp.addStretch()

        ver_bottom = QtWidgets.QLabel("v2.4.7")
        ver_bottom.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver_bottom.setStyleSheet(
            "font-size: 8.5pt; color: rgba(255,255,255,0.17);"
            "letter-spacing: 1.5px; font-weight: 500;"
        )
        lp.addWidget(ver_bottom)

        right_panel = QtWidgets.QWidget()
        rp = QtWidgets.QVBoxLayout(right_panel)
        rp.setContentsMargins(0, 0, 0, 0)
        rp.setSpacing(0)

        top_bar = QtWidgets.QWidget()
        top_bar.setStyleSheet("background: transparent;")
        tb = QtWidgets.QHBoxLayout(top_bar)
        tb.setContentsMargins(36, 30, 28, 0)
        tb.setSpacing(10)

        title_lbl = QtWidgets.QLabel("Soul of Waifu")
        title_lbl.setObjectName("title_label")

        version_badge = QtWidgets.QLabel("v2.4.7")
        version_badge.setObjectName("version_badge")
        version_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_badge.setFixedHeight(22)

        close_x = QtWidgets.QPushButton("X")
        close_x.setObjectName("close_x_btn")
        close_x.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        close_x.setFixedSize(28, 28)
        close_x.setCursor(Qt.CursorShape.PointingHandCursor)
        close_x.clicked.connect(self.accept)

        tb.addWidget(title_lbl)
        tb.addWidget(version_badge, 0, Qt.AlignmentFlag.AlignBottom)
        tb.addStretch()
        tb.addWidget(close_x, 0, Qt.AlignmentFlag.AlignTop)

        rp.addWidget(top_bar)

        tagline_row = QtWidgets.QWidget()
        tagline_row.setStyleSheet("background: transparent;")
        tr = QtWidgets.QHBoxLayout(tagline_row)
        tr.setContentsMargins(36, 5, 28, 14)

        tagline_val = t.get("about_tagline", "AI ROLEPLAY ENGINE")
        tagline_lbl = QtWidgets.QLabel(tagline_val.upper())
        tagline_lbl.setObjectName("tagline_label")
        tr.addWidget(tagline_lbl)
        tr.addStretch()
        rp.addWidget(tagline_row)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content_w = QtWidgets.QWidget()
        cl = QtWidgets.QVBoxLayout(content_w)
        cl.setContentsMargins(36, 0, 36, 16)
        cl.setSpacing(0)

        desc_html = t.get(
            "about_program_description",
            "<p style='line-height:1.80; font-size:14px; "
            "color:rgba(255,255,255,0.62); margin:0 0 14px 0;'>"
            "<b style='color:rgba(255,255,255,0.88); font-weight:600;'>"
            "Soul of Waifu</b> is your ultimate tool for bringing AI-driven "
            "characters to life. With support for advanced APIs from leading AI "
            "platforms and local LLMs, you can customize every aspect of your "
            "character."
            "</p>"
            "<p style='line-height:1.80; font-size:14px; "
            "color:rgba(255,255,255,0.62); margin:0 0 14px 0;'>"
            "Connect a Live2D model, use high-quality TTS/STT, and enjoy "
            "Speech-To-Speech mode to truly talk to your character as if they "
            "were right there with you."
            "</p>"
            "<p style='line-height:1.75; font-size:13px; "
            "color:rgba(255,255,255,0.32); margin:0;'>"
            "Join our community on "
            "<a href='https://discord.gg/6vFtQGVfxM' "
            "style='color:rgba(120,160,255,0.90); text-decoration:none;'>"
            "Discord</a> to share ideas and shape the future of Soul of Waifu."
            "</p>",
        )

        desc_lbl = QtWidgets.QLabel(desc_html)
        desc_lbl.setObjectName("desc_label")
        desc_lbl.setWordWrap(True)
        desc_lbl.setTextFormat(Qt.TextFormat.RichText)
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        desc_lbl.setOpenExternalLinks(True)

        cl.addWidget(desc_lbl)
        cl.addStretch()
        scroll.setWidget(content_w)
        rp.addWidget(scroll, 1)

        rp.addWidget(_make_h_separator())

        footer = QtWidgets.QWidget()
        footer.setStyleSheet("background: transparent;")
        fl = QtWidgets.QHBoxLayout(footer)
        fl.setContentsMargins(36, 12, 28, 20)
        fl.setSpacing(10)

        by_text = t.get("creator_label", "Made by")
        author_lbl = QtWidgets.QLabel(
            f"{by_text} <a href='https://github.com/jofizcd' style='color:rgba(255,255,255,0.8); text-decoration:none;'>jofizcd</a>"
        )
        author_lbl.setObjectName("footer_text")
        author_lbl.setOpenExternalLinks(True)

        website_btn = QtWidgets.QPushButton(t.get("website_btn", "Website"))
        website_btn.setFixedHeight(34)
        website_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        website_btn.clicked.connect(
            lambda: _open_url("https://jofizcd.github.io/soul-of-waifu-site/")
        )

        docs_btn = QtWidgets.QPushButton(t.get("docs_btn", "Docs"))
        docs_btn.setFixedHeight(34)
        docs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        docs_btn.clicked.connect(
            lambda: _open_url("https://jofizcd.github.io/soul-of-waifu-site/docs/")
        )

        donate_btn = QtWidgets.QPushButton(t.get("support_btn", "Support"))
        donate_btn.setObjectName("donate_btn")
        donate_btn.setFixedHeight(34)
        donate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        donate_btn.clicked.connect(
            lambda: _open_url("https://www.donationalerts.com/r/jofizcd")
        )

        fl.addWidget(author_lbl)
        fl.addStretch()
        fl.addWidget(website_btn)
        fl.addWidget(docs_btn)
        fl.addWidget(donate_btn)

        rp.addWidget(footer)

        frame_layout.addWidget(left_panel)
        frame_layout.addWidget(_make_v_separator())
        frame_layout.addWidget(right_panel, 1)

        outer.addWidget(main_frame)

class ResponsiveEmotionLabel(QtWidgets.QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self._movie = None
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        self.setMinimumSize(100, 100)

    def set_emotion_pixmap(self, pixmap):
        self._movie = None
        self.setMovie(None)
        self._pixmap = pixmap
        self._update_display()

    def set_emotion_movie(self, movie):
        self._pixmap = None
        self._movie = movie
        self.setMovie(self._movie)
        self._movie.start()
        self._update_display()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_display()

    def _update_display(self):
        if self.size().isEmpty():
            return
            
        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                self.size(),
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation
            )
            super().setPixmap(scaled)
            
        elif self._movie and self._movie.isValid():
            rect = self._movie.frameRect()
            if not rect.isEmpty():
                orig_size = rect.size()
                scaled_size = orig_size.scaled(
                    self.size(), 
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio
                )
                self._movie.setScaledSize(scaled_size)

class MultiSelectDialog(QDialog):
    _BG       = "#0C0C10"
    _SURF1    = "#111117"
    _SURF2    = "#18181F"
    _SURF3    = "#1F1F27"
    _TEXT     = "#DEDAD2"
    _TEXT_S   = "#6F6B63"
    _BORDER   = "rgba(255,255,255,0.055)"
    _BORDER_M = "rgba(255,255,255,0.10)"
    
    _ACCENT   = "#C49A38"
    _ACC_MUT  = "rgba(196,154,56,0.15)"
    _ACC_GLO  = "rgba(196,154,56,0.32)"
    _ACC_BRT  = "#E2B34C"

    def __init__(self, title, items, selected_items, translations, parent=None):
        super().__init__(parent)
        self.translations = translations
        self.drag_pos = QtCore.QPoint()
        
        self.setWindowTitle(title)
        self.setMinimumSize(460, 620)

        self._init_fonts()
        self.setup_ui(title, items, selected_items)

    def _init_fonts(self):
        def mf(size, weight=QFont.Weight.Normal):
            f = QFont("Inter Tight", size, weight)
            f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            return f

        self.f_title = mf(14, QFont.Weight.Bold)
        self.f_input = mf(10)
        self.f_item  = mf(10, QFont.Weight.Medium)
        self.f_btn   = mf(10, QFont.Weight.DemiBold)

    def setup_ui(self, title, items, selected_items):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.main_frame = QFrame(self)
        self.main_frame.setObjectName("MSMainFrame")
        self.main_frame.setStyleSheet(
            f"QFrame#MSMainFrame {{"
            f"  background-color: {self._BG};"
            f"  border: 1px solid {self._BORDER_M};"
            f"  border-radius: 12px;"
            f"}}"
        )
        layout.addWidget(self.main_frame)

        content_layout = QVBoxLayout(self.main_frame)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(16)

        header_layout = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setFont(self.f_title)
        title_label.setStyleSheet(f"color: {self._TEXT}; background: transparent; border: none;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        content_layout.addLayout(header_layout)

        self.search_bar = QtWidgets.QLineEdit()
        self.search_bar.setObjectName("MSSearchBar")
        self.search_bar.setFont(self.f_input)
        self.search_bar.setPlaceholderText(self.translations.get("lorebook_selector_search", "Search items..."))
        self.search_bar.setFixedHeight(40)
        self.search_bar.setStyleSheet(
            f"QLineEdit#MSSearchBar {{"
            f"  background: {self._SURF2};"
            f"  border: 1px solid {self._BORDER};"
            f"  border-radius: 8px;"
            f"  color: {self._TEXT};"
            f"  padding: 0 14px;"
            f"  selection-background-color: {self._ACC_MUT};"
            f"}}"
            f"QLineEdit#MSSearchBar:focus {{"
            f"  border-color: {self._BORDER_M};"
            f"  background: {self._SURF3};"
            f"}}"
        )
        self.search_bar.textChanged.connect(self.filter_items)
        content_layout.addWidget(self.search_bar)

        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setObjectName("MSList")
        self.list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.list_widget.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list_widget.setFont(self.f_item)
        self.list_widget.setStyleSheet(
            f"QListWidget#MSList {{"
            f"  background: transparent;"
            f"  border: none;"
            f"  outline: none;"
            f"}}"
            f"QListWidget#MSList::item {{"
            f"  background: {self._SURF2};"
            f"  border: 1px solid {self._BORDER};"
            f"  border-radius: 8px;"
            f"  padding: 12px 14px;"
            f"  margin-bottom: 6px;"
            f"  color: {self._TEXT};"
            f"}}"
            f"QListWidget#MSList::item:hover {{"
            f"  background: {self._SURF3};"
            f"  border-color: {self._BORDER_M};"
            f"}}"
            f"QListWidget#MSList::item:selected {{"
            f"  background: transparent;"
            f"}}"
            f"QListWidget#MSList::indicator {{"
            f"  width: 18px;"
            f"  height: 18px;"
            f"  border-radius: 4px;"
            f"  border: 1px solid {self._BORDER_M};"
            f"  background: {self._SURF1};"
            f"  margin-right: 12px;"
            f"}}"
            f"QListWidget#MSList::indicator:checked {{"
            f"  background: {self._ACCENT};"
            f"  border: 1px solid {self._ACC_BRT};"
            f"}}"
            f"QListWidget#MSList::indicator:unchecked:hover {{"
            f"  border-color: {self._TEXT_S};"
            f"}}"
        )
        
        self.list_widget.verticalScrollBar().setStyleSheet(
            f"QScrollBar:vertical {{ background: transparent; width: 6px; margin: 0; }}"
            f"QScrollBar::handle:vertical {{ background: {self._BORDER_M}; border-radius: 3px; min-height: 40px; }}"
            f"QScrollBar::handle:vertical:hover {{ background: {self._TEXT_S}; }}"
            f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}"
        )
        
        for item in items:
            list_item = QtWidgets.QListWidgetItem(item)
            list_item.setFlags(list_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            if item in selected_items:
                list_item.setCheckState(Qt.CheckState.Checked)
            else:
                list_item.setCheckState(Qt.CheckState.Unchecked)
            self.list_widget.addItem(list_item)
        
        content_layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.cancel_btn = QPushButton(self.translations.get("character_edit_cancel", "Cancel"))
        self.cancel_btn.setObjectName("MSBtnCancel")
        self.cancel_btn.setFont(self.f_btn)
        self.cancel_btn.setFixedHeight(40)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setStyleSheet(
            f"QPushButton#MSBtnCancel {{"
            f"  background: transparent;"
            f"  color: {self._TEXT_S};"
            f"  border: 1px solid {self._BORDER};"
            f"  border-radius: 8px;"
            f"}}"
            f"QPushButton#MSBtnCancel:hover {{"
            f"  background: {self._SURF2};"
            f"  color: {self._TEXT};"
            f"  border-color: {self._BORDER_M};"
            f"}}"
        )
        self.cancel_btn.clicked.connect(self.reject)
        
        self.ok_btn = QPushButton(self.translations.get("lorebook_selector_apply", "Apply Changes"))
        self.ok_btn.setObjectName("MSBtnApply")
        self.ok_btn.setFont(self.f_btn)
        self.ok_btn.setFixedHeight(40)
        self.ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ok_btn.setStyleSheet(
            f"QPushButton#MSBtnApply {{"
            f"  background: {self._ACC_MUT};"
            f"  border: 1px solid {self._ACC_GLO};"
            f"  border-radius: 8px;"
            f"  color: {self._ACCENT};"
            f"}}"
            f"QPushButton#MSBtnApply:hover {{"
            f"  background: rgba(196,154,56,0.27);"
            f"  border-color: rgba(196,154,56,0.52);"
            f"  color: {self._ACC_BRT};"
            f"}}"
        )
        self.ok_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.cancel_btn, 1)
        btn_layout.addWidget(self.ok_btn, 2)
        content_layout.addLayout(btn_layout)

    def filter_items(self, text):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def get_selected_items(self):
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(item.text())
        return selected

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self.drag_pos.isNull():
            self.move(self.pos() + event.globalPosition().toPoint() - self.drag_pos)
            self.drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = QtCore.QPoint()

class UpdaterDialog(QDialog):
    _BG       = "#0C0C10"
    _SURF1    = "#111117"
    _SURF2    = "#18181F"
    _SURF3    = "#1F1F27"
    _TEXT     = "#DEDAD2"
    _TEXT_S   = "#6F6B63"
    _BORDER   = "rgba(255,255,255,0.055)"
    _BORDER_M = "rgba(255,255,255,0.10)"
    
    _BLUE     = "#4BB8FF"
    _BLUE_MUT = "rgba(75, 184, 255, 0.15)"
    _BLUE_GLO = "rgba(75, 184, 255, 0.35)"
    
    _DANGER   = "#C44040"
    _GREEN    = "#4ADE80"
    _ACCENT   = "#C49A38"

    def __init__(self, backend_dir, backend_type="CUDA", translations=None, parent=None):
        super().__init__(parent)
        self.translations = translations
        self.backend_dir = backend_dir
        
        self.setWindowTitle(self.translations.get("llama_cpp_updater", "LLAMA.CPP Updater"))
        self.setWindowIcon(QIcon("app/gui/icons/logotype.ico"))
        self.setFixedSize(700, 580)
        
        self.setWindowFlags(
            QtCore.Qt.WindowType.Dialog 
            | QtCore.Qt.WindowType.WindowCloseButtonHint
        )

        self.updater = LlamaUpdater(backend_dir)
        self.backend_type = backend_type
        self.latest_asset_urls = []
        self.latest_version_tag = None

        self._init_fonts()
        self._apply_base_palette()
        self.setup_ui()
        
        asyncio.create_task(self.check_api())

    def _init_fonts(self):
        def mf(size, weight=QFont.Weight.Normal):
            f = QFont("Inter Tight", size, weight)
            f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            return f

        self.f_title = mf(13, QFont.Weight.Bold)
        self.f_label = mf(10, QFont.Weight.Bold)
        self.f_body  = mf(10, QFont.Weight.Medium)
        self.f_btn   = mf(10, QFont.Weight.DemiBold)

    def _apply_base_palette(self):
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor(self._BG))
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_toolbar())
        root.addWidget(self._build_body(), 1)
        root.addWidget(self._build_footer())
        
        self.updater.progress_signal.connect(self.update_progress)
        self.updater.finished_signal.connect(self.on_finished)

    def _build_toolbar(self):
        bar = QFrame()
        bar.setFixedHeight(56)
        bar.setStyleSheet(
            f"background: {self._SURF1};"
            f"border-bottom: 1px solid {self._BORDER};"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(12)

        title_lbl = QLabel(self.translations.get("llama_cpp_updater", "LLAMA.CPP UPDATER"))
        title_lbl.setFont(self.f_title)
        title_lbl.setStyleSheet(f"color: {self._TEXT}; border: none;")

        sep = QFrame()
        sep.setFixedSize(1, 24)
        sep.setStyleSheet(f"background: {self._BORDER}; border: none;")

        sub_lbl = QLabel(self.translations.get("updater_subtitle", "BACKEND ENGINE"))
        sub_lbl.setFont(self.f_label)
        sub_lbl.setStyleSheet(f"color: {self._TEXT_S}; border: none;")

        lay.addWidget(title_lbl)
        lay.addWidget(sep)
        lay.addWidget(sub_lbl)
        lay.addStretch()

        return bar

    def _build_body(self):
        body = QFrame()
        body.setStyleSheet(f"background: {self._BG}; border: none;")
        lay = QVBoxLayout(body)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        info_layout = QHBoxLayout()
        
        lbl_target_tr = self.translations.get("lbl_target_tr", "Target:")
        self.lbl_target = QLabel(f"{lbl_target_tr} <span style='color: {self._BLUE};'>{self.backend_type.upper()}</span>")
        self.lbl_target.setFont(self.f_body)
        self.lbl_target.setStyleSheet(f"color: {self._TEXT};")
        
        self.lbl_current_ver = QLabel(self.translations.get("checking_current_build", "Current: Checking..."))
        self.lbl_current_ver.setFont(self.f_body)
        self.lbl_current_ver.setStyleSheet(f"color: {self._TEXT_S};")
        
        info_layout.addWidget(self.lbl_target)
        info_layout.addStretch()
        info_layout.addWidget(self.lbl_current_ver)
        lay.addLayout(info_layout)

        self.release_notes = QtWidgets.QTextBrowser()
        self.release_notes.setOpenExternalLinks(True)
        self.release_notes.setFont(self.f_body)
        
        lbl_release_notes_tr = self.translations.get("lbl_release_notes_tr", "Contacting GitHub API...")
        self.release_notes.setHtml(f"<p style='text-align: center; color: {self._TEXT_S}; margin-top: 60px;'>{lbl_release_notes_tr}</p>")
        self.release_notes.setStyleSheet(
            f"QTextBrowser {{"
            f"  background: {self._SURF2};"
            f"  border: 1px solid {self._BORDER};"
            f"  border-radius: 8px;"
            f"  color: {self._TEXT};"
            f"  padding: 12px;"
            f"}}"
        )
        self.release_notes.verticalScrollBar().setStyleSheet(
            f"QScrollBar:vertical {{ background: transparent; width: 6px; margin: 0; }}"
            f"QScrollBar::handle:vertical {{ background: {self._BORDER_M}; border-radius: 3px; min-height: 30px; }}"
            f"QScrollBar::handle:vertical:hover {{ background: {self._TEXT_S}; }}"
            f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}"
        )
        lay.addWidget(self.release_notes, 1)

        self.status_label = QLabel("")
        self.status_label.setFont(self.f_body)
        self.status_label.setStyleSheet(f"color: {self._TEXT_S};")
        lay.addWidget(self.status_label)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setFixedHeight(18)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        self.progress_bar.setFont(self.f_label)
        self.progress_bar.setStyleSheet(
            f"QProgressBar {{"
            f"  border: 1px solid {self._BORDER};"
            f"  border-radius: 4px;"
            f"  text-align: center;"
            f"  color: {self._TEXT};"
            f"  background: {self._SURF2};"
            f"}}"
            f"QProgressBar::chunk {{"
            f"  background: {self._BLUE};"
            f"  border-radius: 3px;"
            f"}}"
        )
        lay.addWidget(self.progress_bar)

        return body

    def _build_footer(self):
        bar = QFrame()
        bar.setFixedHeight(64)
        bar.setStyleSheet(
            f"background: {self._SURF1};"
            f"border-top: 1px solid {self._BORDER};"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(24, 0, 24, 0)
        lay.setSpacing(12)

        self.btn_rollback = QPushButton(self.translations.get("rollback_btn", "Rollback"))
        self.btn_rollback.setToolTip(self.translations.get("rollback_btn_tooltip", "Restore previous version"))
        self.btn_rollback.setFont(self.f_btn)
        self.btn_rollback.setFixedSize(120, 36)
        self.btn_rollback.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_rollback.setStyleSheet(
            f"QPushButton {{ background: transparent; border: 1px solid {self._BORDER}; border-radius: 6px; color: {self._TEXT_S}; }}"
            f"QPushButton:hover {{ background: {self._SURF2}; border-color: {self._BORDER_M}; color: {self._TEXT}; }}"
            f"QPushButton:disabled {{ color: rgba(255,255,255,0.2); border-color: transparent; }}"
        )

        lay.addWidget(self.btn_rollback)
        lay.addStretch()

        self.btn_cancel = QPushButton(self.translations.get("cancel", "Cancel"))
        self.btn_cancel.setFont(self.f_btn)
        self.btn_cancel.setFixedSize(100, 36)
        self.btn_cancel.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setStyleSheet(self.btn_rollback.styleSheet())

        self.btn_update = QPushButton(self.translations.get("update_now_btn", "Update Now"))
        self.btn_update.setFont(self.f_btn)
        self.btn_update.setFixedSize(140, 36)
        self.btn_update.setEnabled(False)
        self.btn_update.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_update.setStyleSheet(
            f"QPushButton {{ background: {self._BLUE_MUT}; border: 1px solid {self._BLUE_GLO}; border-radius: 6px; color: {self._BLUE}; }}"
            f"QPushButton:hover {{ background: rgba(75, 184, 255, 0.25); border-color: rgba(75, 184, 255, 0.55); color: {self._BLUE}; }}"
            f"QPushButton:disabled {{ background: {self._SURF2}; border: 1px solid {self._BORDER}; color: {self._TEXT_S}; }}"
        )

        lay.addWidget(self.btn_cancel)
        lay.addWidget(self.btn_update)

        self.btn_cancel.clicked.connect(self.close)
        self.btn_update.clicked.connect(self.start_update)
        self.btn_rollback.clicked.connect(self.start_rollback)

        return bar

    def _clean_release_notes(self, raw_text: str) -> str:
        if not raw_text:
            return self.translations.get("no_release_notes", "No release notes provided.")

        cutoff_keywords = ["macOS/iOS:", "macOS Apple Silicon", "Android:"]
        for kw in cutoff_keywords:
            if kw in raw_text:
                raw_text = raw_text.split(kw)[0]

        text = re.sub(r'\n{3,}', '\n\n', raw_text)
        
        html_lines = []
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            if line.startswith("fix:") or line.startswith("bug:"):
                html_lines.append(f"<li style='color: {self._DANGER}; margin-bottom: 4px;'><b>Fix:</b> {line[4:].strip()}</li>")
            elif line.startswith("feat:") or line.startswith("feature:"):
                html_lines.append(f"<li style='color: {self._GREEN}; margin-bottom: 4px;'><b>Feature:</b> {line[5:].strip()}</li>")
            elif line.startswith("refactor:"):
                html_lines.append(f"<li style='color: {self._BLUE}; margin-bottom: 4px;'><b>Refactor:</b> {line[9:].strip()}</li>")
            elif line.startswith("docs:") or line.startswith("chore:"):
                html_lines.append(f"<li style='color: {self._TEXT_S}; margin-bottom: 4px;'><i>{line}</i></li>")
            else:
                html_lines.append(f"<p style='margin-bottom: 6px; color: {self._TEXT};'>{line}</p>")

        final_html = "<ul style='margin-top: 5px; padding-left: 20px;'>" + "".join(html_lines) + "</ul>"
        return final_html

    async def check_api(self):
        current_version = self.updater._get_current_version(self.backend_type)
        self.lbl_current_ver.setText(f"{self.translations.get('current_ver_label', 'Current:')} {current_version}")
        
        data, err = await self.updater.fetch_latest_release()
        if err:
            self.release_notes.setHtml(f"<p style='color: {self._DANGER};'>{self.translations.get('github_error', 'Error connecting to GitHub')}:<br>{err}</p>")
            self.status_label.setText(self.translations.get("conn_failed", "Connection failed."))
            return

        self.latest_version_tag = data.get("tag_name", "")
        raw_body = data.get("body", "")
        
        cleaned_html = self._clean_release_notes(raw_body)
        
        final_view = f"""
        <h2 style='color: {self._TEXT}; margin-bottom: 0px;'>{self.translations.get('version_title', 'Version')}: <span style='color: {self._GREEN};'>{self.latest_version_tag}</span></h2>
        <hr style='border: 1px solid {self._BORDER}; margin-bottom: 15px;'>
        {cleaned_html}
        """
        self.release_notes.setHtml(final_view)

        if self.latest_version_tag == current_version:
            self.status_label.setText(self.translations.get("status_up_to_date", "You are up to date!"))
            self.btn_update.setText(self.translations.get("btn_reinstall", "Reinstall"))
        else:
            self.status_label.setText(self.translations.get("status_ready_download", "Ready to download."))

        urls = self.updater._match_assets(data.get("assets", []), self.backend_type)
        if urls:
            self.latest_asset_urls = urls
            self.btn_update.setEnabled(True)
        else:
            self.status_label.setText(self.translations.get("status_no_binary", "No compatible binary found."))
            self.status_label.setStyleSheet(f"color: {self._DANGER};")

    def start_update(self):
        self.btn_update.setEnabled(False)
        self.btn_rollback.setEnabled(False)
        self.progress_bar.show()
        asyncio.create_task(self.updater.download_and_install(
            self.latest_asset_urls, 
            self.backend_type, 
            self.latest_version_tag
        ))

    def start_rollback(self):
        self.btn_update.setEnabled(False)
        self.btn_rollback.setEnabled(False)
        self.status_label.setText(self.translations.get("status_restoring", "Restoring backup..."))
        asyncio.create_task(self.execute_rollback())
        
    async def execute_rollback(self):
        success, msg = await self.updater.restore_backup(self.backend_type)
        self.on_finished(success, msg)

    def update_progress(self, percent, text):
        self.progress_bar.setValue(percent)
        self.status_label.setText(text)

    def on_finished(self, success, message):
        self.progress_bar.hide()
        self.status_label.setText(message)
        if success:
            self.status_label.setStyleSheet(f"color: {self._GREEN};")
            self.btn_update.setText(self.translations.get("btn_done", "Done"))
            self.btn_update.clicked.disconnect()
            self.btn_update.clicked.connect(self.accept)
            self.btn_update.setEnabled(True)
            self.lbl_current_ver.setText(f"{self.translations.get('current_ver_label', 'Current:')} {self.latest_version_tag}")
        else:
            self.status_label.setStyleSheet(f"color: {self._DANGER};")
            self.btn_update.setEnabled(True)
            self.btn_rollback.setEnabled(True)

class SowToastManager:
    _instance = None
 
    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
 
    def __init__(self):
        self._toasts: list["SowToast"] = []
        self._margin = 16
        self._spacing = 10
 
    def show(self, parent, title="", text="", msg_type="info", duration=4000):
        self._prune_toasts()
        
        toast = SowToast(parent, title, text, msg_type, duration)
        toast.closed.connect(lambda t=toast: self._on_closed(t))
        self._toasts.append(toast)
        self._reposition(animate=False)
        toast.show_toast()
 
    def _on_closed(self, toast):
        try:
            if toast in self._toasts:
                self._toasts.remove(toast)
        except RuntimeError:
            pass
        self._reposition(animate=True)
 
    def _prune_toasts(self):
        valid_toasts = []
        for toast in self._toasts:
            try:
                _ = toast.parent()
                valid_toasts.append(toast)
            except RuntimeError:
                pass
        self._toasts = valid_toasts

    def _reposition(self, animate=False):
        self._prune_toasts()
        
        if not self._toasts:
            return
 
        try:
            parent = self._toasts[0].parent()
        except RuntimeError:
            return

        if parent is None:
            return
 
        try:
            rect = parent.rect()
            y = rect.bottom() - self._margin
     
            for toast in reversed(self._toasts):
                try:
                    toast.adjustSize()
                    w = toast.width()
                    h = toast.height()
                    x = rect.right() - w - self._margin
                    target_y = y - h
         
                    if animate:
                        anim = QPropertyAnimation(toast, b"geometry")
                        anim.setDuration(250)
                        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                        anim.setEndValue(QtCore.QRect(x, target_y, w, h))
                        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
                        toast._reposition_anim = anim
                    else:
                        toast.setGeometry(x, target_y, w, h)
         
                    toast.raise_()
                    y = target_y - self._spacing
                except RuntimeError:
                    continue
        except RuntimeError:
            pass

class _ProgressBar(QtWidgets.QWidget):
    def __init__(self, parent, color: str, duration_ms: int):
        super().__init__(parent)
        self._color = QColor(color)
        self._progress = 1.0
        self._duration = duration_ms
        self._anim = QPropertyAnimation(self, b"progress")
        self._anim.setDuration(duration_ms)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.Type.Linear)
        self.setFixedHeight(3)
 
    def start(self):
        self._anim.start()
 
    @pyqtProperty(float)
    def progress(self):
        return self._progress
 
    @progress.setter
    def progress(self, v):
        self._progress = v
        self.update()
 
    def _get_full_shape(self, rect: QtCore.QRect, s_len: int):
        path = QtGui.QPainterPath()
        h = float(rect.height())
        w = float(rect.width())
        left = float(rect.left())
        top = float(rect.top())
        
        path.moveTo(left, top + h)
        
        path.cubicTo(left + s_len * 0.4, top + h, 
                     left + s_len * 0.6, top, 
                     left + s_len, top)
        
        path.lineTo(left + w - s_len, top)
        
        path.cubicTo(left + w - s_len * 0.6, top, 
                     left + w - s_len * 0.4, top + h, 
                     left + w, top + h)
        
        return path

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        margin = 10
        slope_len = 25
        
        full_rect = self.rect().adjusted(margin, 0, -margin, 0)
        
        shape_path = self._get_full_shape(full_rect, slope_len)
 
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 15))
        p.drawPath(shape_path)
 
        if self._progress > 0:
            p.save()
            
            p.setClipPath(shape_path)
            
            fill_w = full_rect.width() * self._progress
            
            grad = QLinearGradient(full_rect.left(), 0, full_rect.left() + fill_w, 0)
            grad.setColorAt(0, self._color.darker(115))
            grad.setColorAt(1, self._color)
            
            p.setBrush(grad)
            p.drawRect(QtCore.QRectF(full_rect.left(), 0, fill_w, self.height()))
            
            p.restore()
 
class SowToast(QtWidgets.QWidget):
    closed = QtCore.pyqtSignal()
 
    icons = {
        "success": ("✓", "#4ADE80"),
        "error":   ("✕", "#F87171"),
        "info":    ("i", "#60A5FA"),
        "warning": ("!", "#FBBF24"),
    }
 
    def __init__(self, parent, title: str, text: str, msg_type: str, duration: int):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
 
        self._duration = duration
        self._hovered = False
        icon_char, color = self.icons.get(msg_type, ("i", "#60A5FA"))
        self._accent = QColor(color)
 
        self._build_ui(title, text, icon_char, color, duration)
        self.setFixedWidth(360)
        self.adjustSize()

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)
 
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._slide_out)
 
    def _build_ui(self, title, text, icon_char, color, duration):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
 
        self._card = QtWidgets.QFrame()
        self._card.setObjectName("Card")
 
        self._card.setStyleSheet("""
            QFrame#Card {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(28, 28, 35, 252),
                    stop:1 rgba(18, 18, 24, 252)
                );
                border: 1px solid rgba(255, 255, 255, 0.13);
                border-radius: 12px;
            }
        """)
 
        card_layout = QtWidgets.QVBoxLayout(self._card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        body = QtWidgets.QHBoxLayout()
        body.setContentsMargins(14, 14, 14, 12)
        body.setSpacing(12)

        icon_wrap = QtWidgets.QWidget()
        icon_wrap.setFixedSize(32, 32)
        icon_wrap.setStyleSheet(f"""
            background: rgba({self._accent.red()},{self._accent.green()},{self._accent.blue()},40);
            border-radius: 16px;
        """)
        icon_lbl = QtWidgets.QLabel(icon_char, icon_wrap)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setGeometry(0, 0, 32, 32)
        fnt = QFont("Inter Tight", 13, QFont.Weight.Bold)
        fnt.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        icon_lbl.setFont(fnt)
        icon_lbl.setStyleSheet(f"color: {color}; background: transparent;")
        body.addWidget(icon_wrap, 0, Qt.AlignmentFlag.AlignTop)

        txt_col = QtWidgets.QVBoxLayout()
        txt_col.setSpacing(2)
 
        if title:
            lbl_title = QtWidgets.QLabel(title)
            f = QFont("Inter Tight", 12, QFont.Weight.DemiBold)
            f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            lbl_title.setFont(f)
            lbl_title.setStyleSheet(f"color: {color};")
            txt_col.addWidget(lbl_title)
 
        if text:
            lbl_body = QtWidgets.QLabel(text)
            f2 = QFont("Inter", 10)
            f2.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            lbl_body.setFont(f2)
            lbl_body.setStyleSheet("color: rgba(226,232,240,0.85);")
            lbl_body.setWordWrap(True)
            lbl_body.setTextFormat(Qt.TextFormat.RichText)
            txt_col.addWidget(lbl_body)
 
        body.addLayout(txt_col, 1)
 
        btn_close = QtWidgets.QPushButton("✕")
        btn_close.setFixedSize(24, 24)
        f3 = QFont("Inter", 9)
        f3.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        btn_close.setFont(f3)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: rgba(255,255,255,0.3);
                border: none;
                border-radius: 12px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.1);
                color: rgba(255,255,255,0.8);
            }
        """)
        btn_close.clicked.connect(self._slide_out)
        body.addWidget(btn_close, 0, Qt.AlignmentFlag.AlignTop)
 
        card_layout.addLayout(body)

        self._pbar = _ProgressBar(self._card, color, duration)
        pbar_wrap = QtWidgets.QWidget()
        pbar_wrap.setFixedHeight(3)
        pw_lay = QtWidgets.QHBoxLayout(pbar_wrap)
        pw_lay.setContentsMargins(0, 0, 0, 0)
        pw_lay.addWidget(self._pbar)
        card_layout.addWidget(pbar_wrap)
 
        root.addWidget(self._card)

    def show_toast(self):
        self.show()
        self.raise_()
 
        self._anim_in = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._anim_in.setDuration(220)
        self._anim_in.setStartValue(0.0)
        self._anim_in.setEndValue(1.0)
        self._anim_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim_in.start()
 
        self._pbar.start()
        self._timer.start(self._duration)
 
    def _slide_out(self):
        if hasattr(self, "_anim_out") and \
           self._anim_out.state() == QPropertyAnimation.State.Running:
            return
 
        self._timer.stop()
 
        self._anim_out = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._anim_out.setDuration(280)
        self._anim_out.setStartValue(self._opacity_effect.opacity())
        self._anim_out.setEndValue(0.0)
        self._anim_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._anim_out.finished.connect(self._cleanup)
        self._anim_out.start()
 
    def _cleanup(self):
        self.closed.emit()
        self.deleteLater()
 
    def enterEvent(self, _):
        self._hovered = True
        self._timer.stop()
        if self._pbar._anim.state() == QPropertyAnimation.State.Running:
            self._pbar._anim.pause()
 
    def leaveEvent(self, _):
        self._hovered = False
        if self._pbar._anim.state() == QPropertyAnimation.State.Paused:
            remaining = int(self._duration * self._pbar._progress)
            self._pbar._anim.resume()
            self._timer.start(remaining)
 
def sow_toast(parent=None, title="", text="", msg_type="info", duration=4000):
    """
    msg_type: "info" | "success" | "error" | "warning"
    """
    SowToastManager.instance().show(parent, title, text, msg_type, duration)

class CallModeDialog(QtWidgets.QDialog):
    """
    Small dialog shown from a character card's Call button, letting the user
    pick which calling mode to launch with (Soul of Waifu System or Soul
    Companion).
    """
    def __init__(self, parent=None, translations=None, current_mode=0):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.translations = translations or {}
        self._overlay = None
        self.selected_mode = current_mode

        self._build_ui(current_mode)

    def _build_ui(self, current_mode):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self._card = QtWidgets.QFrame()
        self._card.setObjectName("Card")
        self._card.setFixedWidth(420)
        self._card.setStyleSheet("""
            QFrame#Card {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgb(26, 26, 34), stop:1 rgb(18, 18, 26));
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
            }
        """)

        lay = QtWidgets.QVBoxLayout(self._card)
        lay.setContentsMargins(28, 26, 28, 24)
        lay.setSpacing(0)

        f_title = QFont("Inter Tight", 15, QFont.Weight.Bold)
        f_title.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        lbl_title = QtWidgets.QLabel(self.translations.get("call_mode_dialog_title", "Choose Call Mode"))
        lbl_title.setFont(f_title)
        lbl_title.setStyleSheet("color: #E2E8F0; background: transparent;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl_title)

        lay.addSpacing(6)

        f_sub = QFont("Inter", 10)
        f_sub.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        lbl_sub = QtWidgets.QLabel(self.translations.get(
            "call_mode_dialog_subtitle", "You can switch modes any time — this won't change your default Settings."
        ))
        lbl_sub.setFont(f_sub)
        lbl_sub.setWordWrap(True)
        lbl_sub.setStyleSheet("color: rgba(226,232,240,0.5); background: transparent;")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl_sub)

        lay.addSpacing(20)

        options_row = QtWidgets.QHBoxLayout()
        options_row.setSpacing(12)

        self._option_buttons = {}

        def make_option(mode_idx, icon_text, title_text, desc_text, accent):
            btn = QtWidgets.QFrame()
            btn.setObjectName("ModeOption")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(170)

            v = QtWidgets.QVBoxLayout(btn)
            v.setContentsMargins(16, 18, 16, 16)
            v.setSpacing(6)

            f_icon = QFont("Inter", 22)
            f_icon.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            icon_lbl = QtWidgets.QLabel(icon_text)
            icon_lbl.setFont(f_icon)
            icon_lbl.setStyleSheet(f"color: {accent}; background: transparent; border: none;")
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v.addWidget(icon_lbl)

            v.addSpacing(4)

            f_opt_title = QFont("Inter Tight", 11, QFont.Weight.DemiBold)
            f_opt_title.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            opt_title_lbl = QtWidgets.QLabel(title_text)
            opt_title_lbl.setFont(f_opt_title)
            opt_title_lbl.setWordWrap(True)
            opt_title_lbl.setStyleSheet("color: #E2E8F0; background: transparent; border: none;")
            opt_title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v.addWidget(opt_title_lbl)

            f_opt_desc = QFont("Inter", 9)
            f_opt_desc.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            opt_desc_lbl = QtWidgets.QLabel(desc_text)
            opt_desc_lbl.setFont(f_opt_desc)
            opt_desc_lbl.setWordWrap(True)
            opt_desc_lbl.setStyleSheet("color: rgba(226,232,240,0.5); background: transparent; border: none;")
            opt_desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v.addWidget(opt_desc_lbl, 1)

            def _set_style(selected):
                border_color = accent if selected else "rgba(255,255,255,0.1)"
                bg = f"rgba(96,165,250,0.08)" if selected and accent == "#60A5FA" else \
                     (f"rgba(167,139,250,0.08)" if selected else "rgba(255,255,255,0.03)")
                btn.setStyleSheet(f"""
                    QFrame#ModeOption {{
                        background: {bg};
                        border: 1.5px solid {border_color};
                        border-radius: 12px;
                    }}
                    QFrame#ModeOption:hover {{
                        border: 1.5px solid {accent};
                    }}
                """)

            _set_style(mode_idx == current_mode)
            btn._set_selected = _set_style

            def _on_click(event, m=mode_idx):
                self.selected_mode = m
                for idx, b in self._option_buttons.items():
                    b._set_selected(idx == m)

            btn.mousePressEvent = _on_click

            def _on_double_click(event, m=mode_idx):
                self.selected_mode = m
                self.accept()

            btn.mouseDoubleClickEvent = _on_double_click

            self._option_buttons[mode_idx] = btn
            return btn

        sow_btn = make_option(
            0, "🖥️",
            self.translations.get("call_mode_sow_title", "Soul of Waifu System"),
            self.translations.get("call_mode_sow_desc", "Full-screen call window with an interactive model."),
            "#60A5FA"
        )
        companion_btn = make_option(
            1, "🪄",
            self.translations.get("call_mode_companion_title", "Soul Companion"),
            self.translations.get("call_mode_companion_desc", "A frameless desktop companion that stays on top of your other windows."),
            "#A78BFA"
        )

        options_row.addWidget(sow_btn)
        options_row.addWidget(companion_btn)
        lay.addLayout(options_row)

        lay.addSpacing(22)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        line.setStyleSheet("background: rgba(255,255,255,0.07); max-height: 1px; border: none;")
        lay.addWidget(line)
        lay.addSpacing(18)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(10)

        f_btn = QFont("Inter Tight", 11, QFont.Weight.DemiBold)
        f_btn.setHintingPreference(QFont.HintingPreference.PreferNoHinting)

        btn_cancel = QtWidgets.QPushButton(self.translations.get("call_mode_dialog_cancel", "Cancel"))
        btn_cancel.setFixedHeight(40)
        btn_cancel.setFont(f_btn)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 10px;
                color: rgba(226,232,240,0.7);
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.1);
                border-color: rgba(255,255,255,0.2);
                color: #E2E8F0;
            }
        """)
        btn_cancel.clicked.connect(self.reject)

        btn_confirm = QtWidgets.QPushButton(self.translations.get("call_mode_dialog_confirm", "Start Call"))
        btn_confirm.setFixedHeight(40)
        btn_confirm.setFont(f_btn)
        btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_confirm.setStyleSheet("""
            QPushButton {
                background: rgba(96,165,250,0.12);
                border: 1px solid rgba(96,165,250,0.35);
                border-radius: 10px;
                color: #60A5FA;
            }
            QPushButton:hover {
                background: rgba(96,165,250,0.22);
                border-color: rgba(96,165,250,0.6);
            }
        """)
        btn_confirm.clicked.connect(self.accept)

        btn_row.addWidget(btn_cancel, 2)
        btn_row.addWidget(btn_confirm, 3)
        lay.addLayout(btn_row)

        root.addWidget(self._card, 0, Qt.AlignmentFlag.AlignCenter)

    def _show_overlay(self):
        if not self.parent():
            return

        self._overlay = QtWidgets.QWidget(self.parent())
        self._overlay.setGeometry(self.parent().rect())
        self._overlay.show()
        self._overlay.raise_()
        self.raise_()

        self._ov_effect = QGraphicsOpacityEffect(self._overlay)
        self._ov_effect.setOpacity(0.0)
        self._overlay.setGraphicsEffect(self._ov_effect)
        self._overlay.setStyleSheet("background: rgba(0, 0, 0, 180);")

        self._ov_anim_in = QPropertyAnimation(self._ov_effect, b"opacity")
        self._ov_anim_in.setDuration(200)
        self._ov_anim_in.setStartValue(0.0)
        self._ov_anim_in.setEndValue(1.0)
        self._ov_anim_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._ov_anim_in.start()

        self._overlay.mousePressEvent = lambda e: self.reject()

    def _hide_overlay(self, then=None):
        if not self._overlay:
            if then:
                then()
            return

        self._ov_anim_out = QPropertyAnimation(self._ov_effect, b"opacity")
        self._ov_anim_out.setDuration(180)
        self._ov_anim_out.setStartValue(self._ov_effect.opacity())
        self._ov_anim_out.setEndValue(0.0)
        self._ov_anim_out.setEasingCurve(QEasingCurve.Type.InCubic)

        def _cleanup():
            self._overlay.deleteLater()
            self._overlay = None
            if then:
                then()

        self._ov_anim_out.finished.connect(_cleanup)
        self._ov_anim_out.start()

    def _animate_in(self):
        self.setWindowOpacity(0.0)
        self._dlg_anim_in = QPropertyAnimation(self, b"windowOpacity")
        self._dlg_anim_in.setDuration(200)
        self._dlg_anim_in.setStartValue(0.0)
        self._dlg_anim_in.setEndValue(1.0)
        self._dlg_anim_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._dlg_anim_in.start()

    def _animate_out(self, then=None):
        self._dlg_anim_out = QPropertyAnimation(self, b"windowOpacity")
        self._dlg_anim_out.setDuration(160)
        self._dlg_anim_out.setStartValue(self.windowOpacity())
        self._dlg_anim_out.setEndValue(0.0)
        self._dlg_anim_out.setEasingCurve(QEasingCurve.Type.InCubic)
        if then:
            self._dlg_anim_out.finished.connect(then)
        self._dlg_anim_out.start()

    def showEvent(self, event):
        super().showEvent(event)
        if self.parent():
            parent_rect = self.parent().rect()
            parent_global = self.parent().mapToGlobal(parent_rect.topLeft())
            x = parent_global.x() + (parent_rect.width() - self.width()) // 2
            y = parent_global.y() + (parent_rect.height() - self.height()) // 2
            self.move(x, y)
        self._show_overlay()
        self._animate_in()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.accept()

    def reject(self):
        def _finish():
            self._overlay = None
            super(CallModeDialog, self).reject()
        self._animate_out()
        self._hide_overlay(then=_finish)

    def accept(self):
        def _finish():
            self._overlay = None
            super(CallModeDialog, self).accept()
        self._animate_out()
        self._hide_overlay(then=_finish)


class SowConfirmDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, title="", text="",
                 confirm_text="Confirm", cancel_text="Cancel",
                 danger=False):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._danger = danger
        self._accent = "#F87171" if danger else "#60A5FA"
        self._overlay = None

        self._build_ui(title, text, confirm_text, cancel_text)

    def _build_ui(self, title, text, confirm_text, cancel_text):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self._card = QtWidgets.QFrame()
        self._card.setObjectName("Card")
        self._card.setFixedWidth(400)
        self._card.setStyleSheet("""
            QFrame#Card {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgb(26, 26, 34),
                    stop:1 rgb(18, 18, 26));
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
            }
        """)

        lay = QtWidgets.QVBoxLayout(self._card)
        lay.setContentsMargins(28, 28, 28, 24)
        lay.setSpacing(0)

        if self._danger:
            icon_lbl = QtWidgets.QLabel("⚠")
            f_icon = QFont("Inter", 30)
            f_icon.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            icon_lbl.setFont(f_icon)
            icon_lbl.setStyleSheet(f"color: {self._accent}; background: transparent;")
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(icon_lbl)
            lay.addSpacing(10)

        lbl_title = QtWidgets.QLabel(title)
        f_title = QFont("Inter Tight", 15, QFont.Weight.Bold)
        f_title.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        lbl_title.setFont(f_title)
        lbl_title.setStyleSheet(
            f"color: {'#F87171' if self._danger else '#E2E8F0'}; background: transparent;"
        )
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setWordWrap(True)
        lay.addWidget(lbl_title)

        lay.addSpacing(10)

        lbl_text = QtWidgets.QLabel(text)
        f_text = QFont("Inter", 10)
        f_text.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        lbl_text.setFont(f_text)
        lbl_text.setStyleSheet("color: rgba(226,232,240,0.55); background: transparent;")
        lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_text.setWordWrap(True)
        lbl_text.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(lbl_text)

        lay.addSpacing(28)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        line.setStyleSheet(
            "background: rgba(255,255,255,0.07); max-height: 1px; border: none;"
        )
        lay.addWidget(line)
        lay.addSpacing(20)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(10)

        f_btn = QFont("Inter Tight", 11, QFont.Weight.DemiBold)
        f_btn.setHintingPreference(QFont.HintingPreference.PreferNoHinting)

        btn_cancel = QtWidgets.QPushButton(cancel_text)
        btn_cancel.setFixedHeight(40)
        btn_cancel.setFont(f_btn)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 10px;
                color: rgba(226,232,240,0.7);
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.1);
                border-color: rgba(255,255,255,0.2);
                color: #E2E8F0;
            }
            QPushButton:pressed {
                background: rgba(255,255,255,0.07);
            }
        """)
        btn_cancel.clicked.connect(self.reject)

        btn_confirm = QtWidgets.QPushButton(confirm_text)
        btn_confirm.setFixedHeight(40)
        btn_confirm.setFont(f_btn)
        btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)

        if self._danger:
            btn_confirm.setStyleSheet("""
                QPushButton {
                    background: rgba(248,113,113,0.12);
                    border: 1px solid rgba(248,113,113,0.35);
                    border-radius: 10px;
                    color: #F87171;
                }
                QPushButton:hover {
                    background: rgba(248,113,113,0.22);
                    border-color: rgba(248,113,113,0.6);
                }
                QPushButton:pressed {
                    background: rgba(248,113,113,0.15);
                }
            """)
        else:
            btn_confirm.setStyleSheet("""
                QPushButton {
                    background: rgba(96,165,250,0.12);
                    border: 1px solid rgba(96,165,250,0.35);
                    border-radius: 10px;
                    color: #60A5FA;
                }
                QPushButton:hover {
                    background: rgba(96,165,250,0.22);
                    border-color: rgba(96,165,250,0.6);
                }
                QPushButton:pressed {
                    background: rgba(96,165,250,0.15);
                }
            """)

        btn_confirm.clicked.connect(self.accept)

        btn_row.addWidget(btn_cancel, 3)
        btn_row.addWidget(btn_confirm, 2)
        lay.addLayout(btn_row)

        root.addWidget(self._card, 0, Qt.AlignmentFlag.AlignCenter)

    def _show_overlay(self):
        if not self.parent():
            return

        self._overlay = QtWidgets.QWidget(self.parent())
        self._overlay.setGeometry(self.parent().rect())
        self._overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self._overlay.show()
        self._overlay.raise_()
        self.raise_()

        self._ov_effect = QGraphicsOpacityEffect(self._overlay)
        self._ov_effect.setOpacity(0.0)
        self._overlay.setGraphicsEffect(self._ov_effect)
        self._overlay.setStyleSheet("background: rgba(0, 0, 0, 180);")

        self._ov_anim_in = QPropertyAnimation(self._ov_effect, b"opacity")
        self._ov_anim_in.setDuration(200)
        self._ov_anim_in.setStartValue(0.0)
        self._ov_anim_in.setEndValue(1.0)
        self._ov_anim_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._ov_anim_in.start()

        self._overlay.mousePressEvent = lambda e: self.reject()

    def _hide_overlay(self, then=None):
        if not self._overlay:
            if then:
                then()
            return

        self._ov_anim_out = QPropertyAnimation(self._ov_effect, b"opacity")
        self._ov_anim_out.setDuration(180)
        self._ov_anim_out.setStartValue(self._ov_effect.opacity())
        self._ov_anim_out.setEndValue(0.0)
        self._ov_anim_out.setEasingCurve(QEasingCurve.Type.InCubic)

        def _cleanup():
            self._overlay.deleteLater()
            self._overlay = None
            if then:
                then()

        self._ov_anim_out.finished.connect(_cleanup)
        self._ov_anim_out.start()

    def _animate_in(self):
        self.setWindowOpacity(0.0)

        self._dlg_anim_in = QPropertyAnimation(self, b"windowOpacity")
        self._dlg_anim_in.setDuration(200)
        self._dlg_anim_in.setStartValue(0.0)
        self._dlg_anim_in.setEndValue(1.0)
        self._dlg_anim_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._dlg_anim_in.start()

    def _animate_out(self, then=None):
        self._dlg_anim_out = QPropertyAnimation(self, b"windowOpacity")
        self._dlg_anim_out.setDuration(160)
        self._dlg_anim_out.setStartValue(self.windowOpacity())
        self._dlg_anim_out.setEndValue(0.0)
        self._dlg_anim_out.setEasingCurve(QEasingCurve.Type.InCubic)
        if then:
            self._dlg_anim_out.finished.connect(then)
        self._dlg_anim_out.start()

    def showEvent(self, event):
        super().showEvent(event)

        if self.parent():
            parent_rect = self.parent().rect()
            parent_global = self.parent().mapToGlobal(parent_rect.topLeft())
            x = parent_global.x() + (parent_rect.width() - self.width()) // 2
            y = parent_global.y() + (parent_rect.height() - self.height()) // 2
            self.move(x, y)

        self._show_overlay()
        self._animate_in()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.accept()

    def reject(self):
        def _finish():
            self._overlay = None
            super(SowConfirmDialog, self).reject()

        self._animate_out()
        self._hide_overlay(then=_finish)

    def accept(self):
        def _finish():
            self._overlay = None
            super(SowConfirmDialog, self).accept()

        self._animate_out()
        self._hide_overlay(then=_finish)

class SowInputDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, title="Input", label="Enter value:", 
                 text="", placeholder="", confirm_text="Confirm", cancel_text="Cancel"):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._accent = "#60A5FA"
        self._overlay = None

        self._build_ui(title, label, text, placeholder, confirm_text, cancel_text)

    def _build_ui(self, title, label, text, placeholder, confirm_text, cancel_text):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self._card = QtWidgets.QFrame()
        self._card.setObjectName("Card")
        self._card.setFixedWidth(400)
        self._card.setStyleSheet("""
            QFrame#Card {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgb(26, 26, 34),
                    stop:1 rgb(18, 18, 26));
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
            }
        """)

        lay = QtWidgets.QVBoxLayout(self._card)
        lay.setContentsMargins(28, 28, 28, 24)
        lay.setSpacing(0)

        lbl_title = QtWidgets.QLabel(title)
        f_title = QFont("Inter Tight", 15, QFont.Weight.Bold)
        f_title.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        lbl_title.setFont(f_title)
        lbl_title.setStyleSheet(f"color: #E2E8F0; background: transparent;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setWordWrap(True)
        lay.addWidget(lbl_title)

        lay.addSpacing(10)

        lbl_text = QtWidgets.QLabel(label)
        f_text = QFont("Inter", 10)
        f_text.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        lbl_text.setFont(f_text)
        lbl_text.setStyleSheet("color: rgba(226,232,240,0.55); background: transparent;")
        lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_text.setWordWrap(True)
        lay.addWidget(lbl_text)

        lay.addSpacing(16)

        self.input_field = QtWidgets.QLineEdit()
        self.input_field.setFixedHeight(42)
        self.input_field.setText(text)
        self.input_field.setPlaceholderText(placeholder)
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: rgb(18, 18, 26);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                color: #E2E8F0;
                padding: 0 14px;
                selection-background-color: rgba(96, 165, 250, 0.4);
            }
            QLineEdit:focus {
                border: 1px solid rgba(96, 165, 250, 0.5);
                background-color: rgb(22, 22, 30);
            }
        """)
        self.input_field.returnPressed.connect(self.accept)
        lay.addWidget(self.input_field)

        lay.addSpacing(24)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        line.setStyleSheet("background: rgba(255,255,255,0.07); max-height: 1px; border: none;")
        lay.addWidget(line)
        lay.addSpacing(20)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(10)

        f_btn = QFont("Inter Tight", 11, QFont.Weight.DemiBold)
        f_btn.setHintingPreference(QFont.HintingPreference.PreferNoHinting)

        btn_cancel = QtWidgets.QPushButton(cancel_text)
        btn_cancel.setFixedHeight(40)
        btn_cancel.setFont(f_btn)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 10px;
                color: rgba(226,232,240,0.7);
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.1);
                border-color: rgba(255,255,255,0.2);
                color: #E2E8F0;
            }
            QPushButton:pressed {
                background: rgba(255,255,255,0.07);
            }
        """)
        btn_cancel.clicked.connect(self.reject)

        btn_confirm = QtWidgets.QPushButton(confirm_text)
        btn_confirm.setFixedHeight(40)
        btn_confirm.setFont(f_btn)
        btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_confirm.setStyleSheet("""
            QPushButton {
                background: rgba(96,165,250,0.12);
                border: 1px solid rgba(96,165,250,0.35);
                border-radius: 10px;
                color: #60A5FA;
            }
            QPushButton:hover {
                background: rgba(96,165,250,0.22);
                border-color: rgba(96,165,250,0.6);
            }
            QPushButton:pressed {
                background: rgba(96,165,250,0.15);
            }
        """)
        btn_confirm.clicked.connect(self.accept)

        btn_row.addWidget(btn_cancel, 3)
        btn_row.addWidget(btn_confirm, 2)
        lay.addLayout(btn_row)

        root.addWidget(self._card, 0, Qt.AlignmentFlag.AlignCenter)

    def get_text(self):
        return self.input_field.text().strip()

    def _show_overlay(self):
        if not self.parent():
            return

        self._overlay = QtWidgets.QWidget(self.parent())
        self._overlay.setGeometry(self.parent().rect())
        self._overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self._overlay.show()
        self._overlay.raise_()
        self.raise_()

        self._ov_effect = QGraphicsOpacityEffect(self._overlay)
        self._ov_effect.setOpacity(0.0)
        self._overlay.setGraphicsEffect(self._ov_effect)
        self._overlay.setStyleSheet("background: rgba(0, 0, 0, 180);")

        self._ov_anim_in = QPropertyAnimation(self._ov_effect, b"opacity")
        self._ov_anim_in.setDuration(200)
        self._ov_anim_in.setStartValue(0.0)
        self._ov_anim_in.setEndValue(1.0)
        self._ov_anim_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._ov_anim_in.start()

        self._overlay.mousePressEvent = lambda e: self.reject()

    def _hide_overlay(self, then=None):
        if not self._overlay:
            if then:
                then()
            return

        self._ov_anim_out = QPropertyAnimation(self._ov_effect, b"opacity")
        self._ov_anim_out.setDuration(180)
        self._ov_anim_out.setStartValue(self._ov_effect.opacity())
        self._ov_anim_out.setEndValue(0.0)
        self._ov_anim_out.setEasingCurve(QEasingCurve.Type.InCubic)

        def _cleanup():
            self._overlay.deleteLater()
            self._overlay = None
            if then:
                then()

        self._ov_anim_out.finished.connect(_cleanup)
        self._ov_anim_out.start()

    def _animate_in(self):
        self.setWindowOpacity(0.0)

        self._dlg_anim_in = QPropertyAnimation(self, b"windowOpacity")
        self._dlg_anim_in.setDuration(200)
        self._dlg_anim_in.setStartValue(0.0)
        self._dlg_anim_in.setEndValue(1.0)
        self._dlg_anim_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._dlg_anim_in.start()

    def _animate_out(self, then=None):
        self._dlg_anim_out = QPropertyAnimation(self, b"windowOpacity")
        self._dlg_anim_out.setDuration(160)
        self._dlg_anim_out.setStartValue(self.windowOpacity())
        self._dlg_anim_out.setEndValue(0.0)
        self._dlg_anim_out.setEasingCurve(QEasingCurve.Type.InCubic)
        if then:
            self._dlg_anim_out.finished.connect(then)
        self._dlg_anim_out.start()

    def showEvent(self, event):
        super().showEvent(event)

        if self.parent():
            parent_rect = self.parent().rect()
            parent_global = self.parent().mapToGlobal(parent_rect.topLeft())
            x = parent_global.x() + (parent_rect.width() - self.width()) // 2
            y = parent_global.y() + (parent_rect.height() - self.height()) // 2
            self.move(x, y)

        self._show_overlay()
        self._animate_in()
        
        QtCore.QTimer.singleShot(250, self.input_field.setFocus)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()

    def reject(self):
        def _finish():
            self._overlay = None
            super(SowInputDialog, self).reject()

        self._animate_out()
        self._hide_overlay(then=_finish)

    def accept(self):
        def _finish():
            self._overlay = None
            super(SowInputDialog, self).accept()

        self._animate_out()
        self._hide_overlay(then=_finish)

class SowSelectDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, title="Select", label="Select an option:", 
                 items=[], confirm_text="Confirm", cancel_text="Cancel"):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._overlay = None

        self._build_ui(title, label, items, confirm_text, cancel_text)

    def _build_ui(self, title, label, items, confirm_text, cancel_text):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self._card = QtWidgets.QFrame()
        self._card.setObjectName("Card")
        self._card.setFixedWidth(400)
        self._card.setStyleSheet("""
            QFrame#Card {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgb(26, 26, 34), stop:1 rgb(18, 18, 26));
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
            }
        """)

        lay = QtWidgets.QVBoxLayout(self._card)
        lay.setContentsMargins(28, 28, 28, 24)
        lay.setSpacing(0)

        lbl_title = QtWidgets.QLabel(title)
        f_title = QFont("Inter Tight", 15, QFont.Weight.Bold)
        f_title.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        lbl_title.setFont(f_title)
        lbl_title.setStyleSheet("color: #E2E8F0; background: transparent;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl_title)

        lay.addSpacing(10)

        lbl_text = QtWidgets.QLabel(label)
        f_text = QFont("Inter", 10)
        f_text.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        lbl_text.setFont(f_text)
        lbl_text.setStyleSheet("color: rgba(226,232,240,0.55); background: transparent;")
        lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl_text)

        lay.addSpacing(16)

        self.combo_box = QtWidgets.QComboBox()
        self.combo_box.addItems(items)
        self.combo_box.setFixedHeight(42)
        self.combo_box.setStyleSheet("""
            QComboBox {
                background-color: rgba(18, 18, 26);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                color: #E2E8F0;
                padding: 0 14px;
            }
            QComboBox:hover { border: 1px solid rgba(96, 165, 250, 0.3); }
            QComboBox::drop-down { border: none; width: 30px; }
            QComboBox::down-arrow { width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #6F6B63; }
            QComboBox QAbstractItemView {
                background-color: rgb(26, 26, 34);
                color: #E2E8F0;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                selection-background-color: rgba(96, 165, 250, 0.2);
                outline: none;
                padding: 6px;
            }
        """)
        lay.addWidget(self.combo_box)

        lay.addSpacing(24)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        line.setStyleSheet("background: rgba(255,255,255,0.07); max-height: 1px; border: none;")
        lay.addWidget(line)
        lay.addSpacing(20)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(10)

        f_btn = QFont("Inter Tight", 11, QFont.Weight.DemiBold)
        f_btn.setHintingPreference(QFont.HintingPreference.PreferNoHinting)

        btn_cancel = QtWidgets.QPushButton(cancel_text)
        btn_cancel.setFixedHeight(40)
        btn_cancel.setFont(f_btn)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 10px;
                color: rgba(226,232,240,0.7);
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.1);
                border-color: rgba(255,255,255,0.2);
                color: #E2E8F0;
            }
        """)
        btn_cancel.clicked.connect(self.reject)

        btn_confirm = QtWidgets.QPushButton(confirm_text)
        btn_confirm.setFixedHeight(40)
        btn_confirm.setFont(f_btn)
        btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_confirm.setStyleSheet("""
            QPushButton {
                background: rgba(96,165,250,0.12);
                border: 1px solid rgba(96,165,250,0.35);
                border-radius: 10px;
                color: #60A5FA;
            }
            QPushButton:hover {
                background: rgba(96,165,250,0.22);
                border-color: rgba(96,165,250,0.6);
            }
        """)
        btn_confirm.clicked.connect(self.accept)

        btn_row.addWidget(btn_cancel, 3)
        btn_row.addWidget(btn_confirm, 2)
        lay.addLayout(btn_row)

        root.addWidget(self._card, 0, Qt.AlignmentFlag.AlignCenter)

    def get_selected_item(self):
        return self.combo_box.currentText()

    def _show_overlay(self):
        if not self.parent():
            return

        self._overlay = QtWidgets.QWidget(self.parent())
        self._overlay.setGeometry(self.parent().rect())
        self._overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self._overlay.show()
        self._overlay.raise_()
        self.raise_()

        self._ov_effect = QtWidgets.QGraphicsOpacityEffect(self._overlay)
        self._ov_effect.setOpacity(0.0)
        self._overlay.setGraphicsEffect(self._ov_effect)
        self._overlay.setStyleSheet("background: rgba(0, 0, 0, 180);")

        self._ov_anim_in = QtCore.QPropertyAnimation(self._ov_effect, b"opacity")
        self._ov_anim_in.setDuration(200)
        self._ov_anim_in.setStartValue(0.0)
        self._ov_anim_in.setEndValue(1.0)
        self._ov_anim_in.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self._ov_anim_in.start()

        self._overlay.mousePressEvent = lambda e: self.reject()

    def _hide_overlay(self, then=None):
        if not self._overlay:
            if then:
                then()
            return

        self._ov_anim_out = QtCore.QPropertyAnimation(self._ov_effect, b"opacity")
        self._ov_anim_out.setDuration(180)
        self._ov_anim_out.setStartValue(self._ov_effect.opacity())
        self._ov_anim_out.setEndValue(0.0)
        self._ov_anim_out.setEasingCurve(QtCore.QEasingCurve.Type.InCubic)

        def _cleanup():
            self._overlay.deleteLater()
            self._overlay = None
            if then:
                then()

        self._ov_anim_out.finished.connect(_cleanup)
        self._ov_anim_out.start()

    def _animate_in(self):
        self.setWindowOpacity(0.0)

        self._dlg_anim_in = QtCore.QPropertyAnimation(self, b"windowOpacity")
        self._dlg_anim_in.setDuration(200)
        self._dlg_anim_in.setStartValue(0.0)
        self._dlg_anim_in.setEndValue(1.0)
        self._dlg_anim_in.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self._dlg_anim_in.start()

    def _animate_out(self, then=None):
        self._dlg_anim_out = QtCore.QPropertyAnimation(self, b"windowOpacity")
        self._dlg_anim_out.setDuration(160)
        self._dlg_anim_out.setStartValue(self.windowOpacity())
        self._dlg_anim_out.setEndValue(0.0)
        self._dlg_anim_out.setEasingCurve(QtCore.QEasingCurve.Type.InCubic)
        if then:
            self._dlg_anim_out.finished.connect(then)
        self._dlg_anim_out.start()

    def showEvent(self, event):
        super().showEvent(event)

        if self.parent():
            parent_rect = self.parent().rect()
            parent_global = self.parent().mapToGlobal(parent_rect.topLeft())
            x = parent_global.x() + (parent_rect.width() - self.width()) // 2
            y = parent_global.y() + (parent_rect.height() - self.height()) // 2
            self.move(x, y)

        self._show_overlay()
        self._animate_in()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.accept()

    def reject(self):
        def _finish():
            self._overlay = None
            super(SowSelectDialog, self).reject()

        self._animate_out()
        self._hide_overlay(then=_finish)

    def accept(self):
        def _finish():
            self._overlay = None
            super(SowSelectDialog, self).accept()

        self._animate_out()
        self._hide_overlay(then=_finish)

class PersonasEditorDialog(QDialog):
    _BG       = "#0C0C10"
    _SURF1    = "#111117"
    _SURF2    = "#18181F"
    _SURF3    = "#1F1F27"
    _TEXT     = "#DEDAD2"
    _TEXT_S   = "#6F6B63"
    _BORDER   = "rgba(255,255,255,0.055)"
    _BORDER_M = "rgba(255,255,255,0.10)"
    
    _ACCENT   = "#C49A38"  
    _ACC_MUT  = "rgba(196,154,56,0.15)"
    _ACC_GLO  = "rgba(196,154,56,0.32)"
    _ACC_BRT  = "#E2B34C"

    _BLUE     = "#4BB8FF"  
    _BLUE_MUT = "rgba(75, 184, 255, 0.15)"
    _BLUE_GLO = "rgba(75, 184, 255, 0.35)"

    _DANGER   = "#C44040"  
    _DNG_MUT  = "rgba(196,64,64,0.13)"
    _DNG_GLO  = "rgba(196,64,64,0.28)"

    def __init__(self, translations, configuration_settings, main_window, parent=None):
        super().__init__(parent)
        self.translations = translations
        self.configuration_settings = configuration_settings
        self.main_window = main_window

        self.personas_data = self.configuration_settings.get_user_data("personas") or {}
        self.current_default_persona = self.configuration_settings.get_user_data("default_persona")
        self.current_mode = "add"
        self.original_name = None
        self.current_avatar_path = None

        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        self.setWindowTitle(self.translations.get("personas_editor_title", "Personas Editor"))
        self.setWindowIcon(QIcon("app/gui/icons/logotype.ico"))
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setMinimumSize(880, 580)
        self.resize(920, 620)

        self._init_fonts()
        self._apply_base_palette()
        self.setup_ui()
        self._setup_logic()

        self._refresh_personas_list()
        
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
            self._on_item_clicked(self.list_widget.item(0))
        else:
            self._on_add_new_clicked()

    def _init_fonts(self):
        def mf(size, weight=QFont.Weight.Normal):
            f = QFont("Inter Tight", size, weight)
            f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            return f

        self.f_title = mf(14, QFont.Weight.Bold)
        self.f_label = mf(8,  QFont.Weight.Bold)
        self.f_input = mf(10, QFont.Weight.Medium)
        self.f_badge = mf(9,  QFont.Weight.DemiBold)
        self.f_btn   = mf(10, QFont.Weight.DemiBold)
        self.f_list  = mf(11, QFont.Weight.Medium)

    def _apply_base_palette(self):
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor(self._BG))
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setFixedWidth(270)
        sidebar.setStyleSheet(
            f"QFrame {{ background: {self._SURF1}; border-right: 1px solid {self._BORDER}; }}"
        )
        sidebar_lay = QVBoxLayout(sidebar)
        sidebar_lay.setContentsMargins(0, 0, 0, 0)
        sidebar_lay.setSpacing(0)

        sb_header = QFrame()
        sb_header.setFixedHeight(56)
        sb_header.setStyleSheet(f"border-bottom: 1px solid {self._BORDER};")
        sb_h_lay = QVBoxLayout(sb_header)
        sb_h_lay.setContentsMargins(20, 0, 0, 0)
        sb_h_lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        sb_title = QLabel(self.translations.get("personas_editor_library", "PERSONAS LIBRARY"))
        sb_title.setFont(self.f_label)
        sb_title.setStyleSheet(f"color: {self._TEXT_S}; letter-spacing: 1.1px; border: none;")
        sb_h_lay.addWidget(sb_title)
        
        sidebar_lay.addWidget(sb_header)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("ListPersonas")
        self.list_widget.setFont(self.f_list)
        self.list_widget.setStyleSheet(
            f"QListWidget {{ background: transparent; border: none; outline: none; padding: 8px; }}"
            f"QListWidget::item {{ color: {self._TEXT}; padding: 12px; border-radius: 8px; margin-bottom: 4px; border: 1px solid transparent; }}"
            f"QListWidget::item:hover {{ background: {self._SURF2}; border-color: {self._BORDER}; }}"
            f"QListWidget::item:selected {{ background: {self._ACC_MUT}; border-color: {self._ACC_GLO}; color: {self._TEXT}; }}"
        )
        sidebar_lay.addWidget(self.list_widget)

        self.add_new_btn = QPushButton("+ " + self.translations.get("personas_editor_create_new", "Create New Persona"))
        self.add_new_btn.setFont(self.f_btn)
        self.add_new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_new_btn.setFixedHeight(50)
        self.add_new_btn.setStyleSheet(
            f"QPushButton {{ background: {self._SURF2}; color: {self._TEXT_S}; border: none; border-top: 1px solid {self._BORDER}; }}"
            f"QPushButton:hover {{ background: {self._SURF3}; color: {self._TEXT}; }}"
        )
        sidebar_lay.addWidget(self.add_new_btn)

        main_layout.addWidget(sidebar)

        self.editor_area = QFrame()
        self.editor_area.setStyleSheet(f"background: {self._BG}; border: none;")
        editor_lay = QVBoxLayout(self.editor_area)
        editor_lay.setContentsMargins(32, 24, 32, 24)
        editor_lay.setSpacing(16)

        header_row = QHBoxLayout()
        self.header_label = QLabel(self.translations.get("personas_editor_title", "Edit Persona"))
        self.header_label.setFont(self.f_title)
        self.header_label.setStyleSheet(f"color: {self._TEXT};")
        
        self.default_badge = QLabel(self.translations.get("personas_editor_default_badge", "DEFAULT"))
        self.default_badge.setFont(self.f_badge)
        self.default_badge.setStyleSheet(
            f"background: {self._BLUE_MUT}; color: {self._BLUE}; border: 1px solid {self._BLUE_GLO}; border-radius: 6px; padding: 4px 10px; letter-spacing: 1px;"
        )
        self.default_badge.setVisible(False)

        header_row.addWidget(self.header_label)
        header_row.addWidget(self.default_badge)
        header_row.addStretch()
        editor_lay.addLayout(header_row)

        sep = QFrame(); sep.setFixedHeight(1); sep.setStyleSheet(f"background: {self._BORDER}; margin-bottom: 10px;")
        editor_lay.addWidget(sep)

        avatar_row = QHBoxLayout()
        avatar_row.setSpacing(20)
        
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(84, 84)
        self._render_avatar(None)
        
        self.upload_btn = QPushButton(self.translations.get("personas_editor_choose_avatar", "Choose Image"))
        self.upload_btn.setFont(self.f_btn)
        self.upload_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.upload_btn.setFixedSize(150, 34)
        self.upload_btn.setStyleSheet(
            f"QPushButton {{ background: {self._SURF2}; color: {self._TEXT_S}; border: 1px solid {self._BORDER_M}; border-radius: 6px; }}"
            f"QPushButton:hover {{ background: {self._SURF3}; color: {self._TEXT}; }}"
        )

        avatar_info_lay = QVBoxLayout()
        avatar_info_lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        av_hint = QLabel(self.translations.get("personas_editor_avatar_hint", "Recommended size: 256x256 px"))
        av_hint.setFont(self.f_label)
        av_hint.setStyleSheet(f"color: {self._TEXT_S};")
        
        avatar_info_lay.addWidget(self.upload_btn)
        avatar_info_lay.addWidget(av_hint)

        avatar_row.addWidget(self.avatar_label)
        avatar_row.addLayout(avatar_info_lay)
        avatar_row.addStretch()
        editor_lay.addLayout(avatar_row)
        editor_lay.addSpacing(10)

        name_lbl = QLabel(self.translations.get("personas_editor_name", "PERSONA NAME"))
        name_lbl.setFont(self.f_label)
        name_lbl.setStyleSheet(f"color: {self._TEXT_S}; letter-spacing: 0.8px;")
        editor_lay.addWidget(name_lbl)

        self.name_input = QLineEdit()
        self.name_input.setFont(self.f_input)
        self.name_input.setPlaceholderText(self.translations.get("personas_editor_name_placeholder", "E.g. Dark Knight"))
        self.name_input.setStyleSheet(self._s_input())
        self.name_input.setFixedHeight(38)
        editor_lay.addWidget(self.name_input)

        desc_lbl = QLabel(self.translations.get("personas_editor_description", "BACKGROUND & DESCRIPTION"))
        desc_lbl.setFont(self.f_label)
        desc_lbl.setStyleSheet(f"color: {self._TEXT_S}; letter-spacing: 0.8px; margin-top: 10px;")
        editor_lay.addWidget(desc_lbl)

        self.desc_input = QTextEdit()
        self.desc_input.setFont(self.f_input)
        self.desc_input.setPlaceholderText(self.translations.get("personas_editor_description_placeholder", "Describe the persona's role, tone, and backstory..."))
        self.desc_input.setStyleSheet(self._s_input())
        editor_lay.addWidget(self.desc_input, stretch=1)

        footer_row = QHBoxLayout()
        footer_row.setContentsMargins(0, 16, 0, 0)
        
        self.delete_btn = QPushButton(self.translations.get("personas_editor_delete_btn", "DELETE"))
        self.delete_btn.setFont(self.f_btn)
        self.delete_btn.setFixedSize(100, 36)
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: 1px solid {self._DNG_GLO}; border-radius: 6px; color: {self._DANGER}; letter-spacing: 0.5px; }}"
            f"QPushButton:hover {{ background: {self._DNG_MUT}; border-color: rgba(196,64,64,0.45); color: #EE7777; }}"
        )
        
        self.set_default_btn = QPushButton(self.translations.get("personas_editor_default_btn", "SET AS DEFAULT"))
        self.set_default_btn.setFont(self.f_btn)
        self.set_default_btn.setFixedSize(140, 36)
        self.set_default_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_default_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: 1px solid {self._BORDER_M}; border-radius: 6px; color: {self._TEXT}; letter-spacing: 0.5px; }}"
            f"QPushButton:hover {{ background: {self._SURF2}; }}"
        )
        
        self.save_btn = QPushButton(self.translations.get("personas_editor_save", "SAVE PERSONA"))
        self.save_btn.setFont(self.f_btn)
        self.save_btn.setFixedSize(160, 36)
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setStyleSheet(
            f"QPushButton {{ background: {self._ACC_MUT}; border: 1px solid {self._ACC_GLO}; border-radius: 6px; color: {self._ACCENT}; letter-spacing: 0.5px; }}"
            f"QPushButton:hover {{ background: rgba(196,154,56,0.27); border-color: rgba(196,154,56,0.52); color: {self._ACC_BRT}; }}"
        )

        self.token_counter_lbl = QLabel("Tokens: 0")
        self.token_counter_lbl.setFont(self.f_badge)
        self.token_counter_lbl.setStyleSheet(f"color: {self._TEXT_S}; background: transparent; border: none;")

        footer_row.addWidget(self.delete_btn)
        footer_row.addSpacing(16)
        footer_row.addWidget(self.token_counter_lbl)
        footer_row.addStretch()
        footer_row.addWidget(self.set_default_btn)
        footer_row.addWidget(self.save_btn)

        editor_lay.addLayout(footer_row)
        main_layout.addWidget(self.editor_area)

    def _s_input(self):
        return (
            f"QWidget {{"
            f"  background: {self._SURF2};"
            f"  border: 1px solid {self._BORDER};"
            f"  border-radius: 8px;"
            f"  color: {self._TEXT};"
            f"  padding: 10px 14px;"
            f"  selection-background-color: {self._ACC_MUT};"
            f"}}"
            f"QWidget:focus {{"
            f"  border-color: {self._BORDER_M};"
            f"  background: {self._SURF3};"
            f"}}"
        )

    def _setup_logic(self):
        self.upload_btn.clicked.connect(self._choose_avatar)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.add_new_btn.clicked.connect(self._on_add_new_clicked)
        self.save_btn.clicked.connect(self._save_action)
        self.delete_btn.clicked.connect(self._delete_action)
        self.set_default_btn.clicked.connect(self._set_default_action)
        self.name_input.textChanged.connect(self._update_token_count)
        self.desc_input.textChanged.connect(self._update_token_count)

    def _render_avatar(self, path):
        avatar_size = 110
        self.avatar_label.setFixedSize(avatar_size, avatar_size)

        if not path or not os.path.exists(path):
            self.avatar_label.clear()
            self.avatar_label.setText("No Img")
            self.avatar_label.setStyleSheet(
                f"border-radius: {avatar_size//2}px; border: 1px dashed {self._BORDER_M}; background: {self._SURF2}; color: {self._TEXT_S}; font-size: 13px;"
            )
            self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.avatar_label.setGraphicsEffect(None)
            return

        source_pixmap = QPixmap(path)
        if source_pixmap.isNull():
            return

        scaled_pixmap = source_pixmap.scaled(
            avatar_size, avatar_size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )

        x = (scaled_pixmap.width() - avatar_size) // 2
        y = (scaled_pixmap.height() - avatar_size) // 2
        square_pixmap = scaled_pixmap.copy(x, y, avatar_size, avatar_size)

        final_pixmap = QPixmap(avatar_size, avatar_size)
        final_pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(final_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        brush = QtGui.QBrush(square_pixmap)
        painter.setBrush(brush)
        painter.setPen(Qt.GlobalColor.transparent)
        
        painter.drawEllipse(0, 0, avatar_size, avatar_size)
        painter.end()

        self.avatar_label.setPixmap(final_pixmap)
        self.avatar_label.setStyleSheet("border: none; background: transparent;")
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 5)
        self.avatar_label.setGraphicsEffect(shadow)

    def _choose_avatar(self):
        path, _ = QFileDialog.getOpenFileName(self, self.translations.get("personas_editor_choose_avatar", "Choose Avatar"), "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.current_avatar_path = path
            self._render_avatar(path)

    def _refresh_personas_list(self):
        self.list_widget.clear()
        self.current_default_persona = self.configuration_settings.get_user_data("default_persona")

        if self.personas_data:
            for name, data in self.personas_data.items():
                item = QListWidgetItem()
                
                display_name = data.get("user_name", name)
                item.setText(display_name)
                item.setData(Qt.ItemDataRole.UserRole, name)
                item.setSizeHint(QSize(0, 52))
                
                av_path = data.get("user_avatar")
                if av_path and os.path.exists(av_path):
                     item.setIcon(QIcon(av_path))
                else:
                     item.setIcon(QIcon("app/gui/icons/person.png"))
                    
                if name == self.current_default_persona:
                    item.setForeground(QtGui.QBrush(QColor(self._BLUE)))
                
                self.list_widget.addItem(item)

    def _on_item_clicked(self, item):
        self.original_name = item.data(Qt.ItemDataRole.UserRole)
        data = self.personas_data.get(self.original_name)
        
        self.current_mode = "edit"
        self.current_avatar_path = data.get("user_avatar")
        
        self.header_label.setText(self.translations.get("personas_editor_title", "Edit Persona"))
        self.save_btn.setText(self.translations.get("personas_editor_save", "SAVE CHANGES"))
        
        self.name_input.setText(data.get("user_name", ""))
        self.desc_input.setPlainText(data.get("user_description", ""))

        self.delete_btn.setVisible(True)

        if self.original_name == self.current_default_persona:
            self.default_badge.setVisible(True)
            self.set_default_btn.setVisible(False)
        else:
            self.default_badge.setVisible(False)
            self.set_default_btn.setVisible(True)
        
        self._render_avatar(self.current_avatar_path)
        self.editor_area.setVisible(True)

        self._update_token_count()

    def _on_add_new_clicked(self):
        self.list_widget.clearSelection()
        self.current_mode = "add"
        self.original_name = None
        self.current_avatar_path = None
        
        self.header_label.setText(self.translations.get("personas_editor_create_new", "Create New Persona"))
        self.save_btn.setText(self.translations.get("personas_editor_create_btn", "CREATE PERSONA"))

        self.delete_btn.setVisible(False)
        self.set_default_btn.setVisible(False)
        self.default_badge.setVisible(False)
        
        self.name_input.clear()
        self.desc_input.clear()
        self._render_avatar(None)
        
        self.editor_area.setVisible(True)
        self.name_input.setFocus()

        self._update_token_count()

    def _set_default_action(self):
        name = self.original_name
        if name:
            self.configuration_settings.update_user_data("default_persona", name)
            self.current_default_persona = name
            
            self._refresh_personas_list()
            
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == name:
                    self.list_widget.setCurrentItem(item)
                    self._on_item_clicked(item)
                    break

    def _delete_action(self):
        if not self.original_name: 
            return

        title = self.translations.get("personas_editor_confirm_delete", "Confirm Delete")
        message = self.translations.get("personas_editor_confirm_delete_text", f"Are you sure you want to delete persona '{self.original_name}'?")

        dialog = SowConfirmDialog(
            parent=self.main_window, 
            title=title,
            text=message,
            confirm_text="Delete",
            danger=True
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            del self.personas_data[self.original_name]
            
            if self.current_default_persona == self.original_name:
                self.configuration_settings.update_user_data("default_persona", "None")
                self.current_default_persona = "None"
            
            self.configuration_settings.update_user_data("personas", self.personas_data)
            self._refresh_personas_list()
            
            if self.list_widget.count() > 0:
                self.list_widget.setCurrentRow(0)
                self._on_item_clicked(self.list_widget.item(0))
            else:
                self._on_add_new_clicked()

    def _save_action(self):
        name = self.name_input.text().strip()
        description = self.desc_input.toPlainText().strip()
        path = self.current_avatar_path
        
        if not name:
            sow_toast(parent=self.main_window, title="Error", text="Name is required", msg_type="error")
            return

        if self.current_mode == "edit":
            if self.original_name != name:
                if name in self.personas_data:
                    sow_toast(
                        parent=self.main_window,
                        title=self.translations.get("system_error_title", "System Error"),
                        text=self.translations.get("toast_persona_exist", "Persona with this name already exists"),
                        msg_type="error"
                    )
                    return
                
                del self.personas_data[self.original_name]
                if self.current_default_persona == self.original_name:
                    self.configuration_settings.update_user_data("default_persona", name)
            
            self.personas_data[name] = {
                "user_name": name,
                "user_description": description,
                "user_avatar": path
            }
        else:
            if name in self.personas_data:
                sow_toast(
                    parent=self.main_window,
                    title=self.translations.get("system_error_title", "System Error"),
                    text=self.translations.get("toast_persona_exist", "Persona with this name already exists"),
                    msg_type="error"
                )
                return
            
            self.personas_data[name] = {
                "user_name": name,
                "user_description": description,
                "user_avatar": path
            }

        self.configuration_settings.update_user_data("personas", self.personas_data)
        self._refresh_personas_list()
        
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == name:
                self.list_widget.setCurrentItem(item)
                self._on_item_clicked(item)
                break
        
        sow_toast(
            parent=self.main_window,
            title=self.translations.get("toast_success", "Success"),
            text=self.translations.get("toast_saved_successfully", "Saved successfully"),
            msg_type="success"
        )

    def _count_tokens(self, text: str) -> int:
        if not text:
            return 0
        try:
            return len(self.tokenizer.encode(text))
        except Exception:
            return len(text) // 4

    def _update_token_count(self):
        texts = [
            self.name_input.text().strip(),
            self.desc_input.toPlainText().strip()
        ]
        total_tokens = sum(self._count_tokens(t) for t in texts)

        if total_tokens < 250:
            color = "#4ADE80"  # Optimal
            weight_text = "Optimal"
        elif total_tokens < 600:
            color = "#82CDFF"  # Normal
            weight_text = "Normal"
        elif total_tokens < 1200:
            color = "#E2B34C"  # Heavy
            weight_text = "Heavy"
        else:
            color = "#C44040"  # Critical
            weight_text = "Critical"

        self.token_counter_lbl.setText(f"Tokens: {total_tokens} ({weight_text})")
        self.token_counter_lbl.setStyleSheet(
            f"color: {color}; font-family: 'Inter Tight SemiBold'; font-size: 11px; background: transparent; border: none;"
        )

class SystemPromptEditorDialog(QDialog):
    _BG       = "#0C0C10"
    _SURF1    = "#111117"
    _SURF2    = "#18181F"
    _SURF3    = "#1F1F27"
    _TEXT     = "#DEDAD2"
    _TEXT_S   = "#6F6B63"
    _BORDER   = "rgba(255,255,255,0.055)"
    _BORDER_M = "rgba(255,255,255,0.10)"
    
    _ACCENT   = "#C49A38"
    _ACC_MUT  = "rgba(196,154,56,0.15)"
    _ACC_GLO  = "rgba(196,154,56,0.32)"
    _ACC_BRT  = "#E2B34C"

    _BLUE     = "#4BB8FF"
    _BLUE_MUT = "rgba(75, 184, 255, 0.15)"
    _BLUE_GLO = "rgba(75, 184, 255, 0.35)"

    _DANGER   = "#C44040"
    _DNG_MUT  = "rgba(196,64,64,0.13)"
    _DNG_GLO  = "rgba(196,64,64,0.28)"

    def __init__(self, translations, configuration_settings, main_window, parent=None):
        super().__init__(parent)
        self.translations = translations
        self.configuration_settings = configuration_settings
        self.main_window = main_window

        self.setWindowTitle(self.translations.get("system_prompt_editor_title", "System Prompt Editor"))
        self.setWindowIcon(QIcon("app/gui/icons/logotype.ico"))
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setMinimumSize(930, 780)
        self.resize(930, 780)

        self._init_fonts()
        self._apply_base_palette()
        self.setup_ui()
        self._setup_logic()

        self._load_presets()
        self._update_preset_combo()
        self._apply_current_preset()

    def _init_fonts(self):
        def mf(size, weight=QFont.Weight.Normal):
            f = QFont("Inter Tight", size, weight)
            f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            return f

        self.f_title = mf(13, QFont.Weight.Bold)
        self.f_label = mf(8,  QFont.Weight.Bold)
        self.f_input = mf(10, QFont.Weight.Medium)
        self.f_btn   = mf(10, QFont.Weight.DemiBold)

    def _apply_base_palette(self):
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor(self._BG))
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_toolbar())

        body = QFrame()
        body.setStyleSheet(f"background: {self._BG}; border: none;")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(24, 20, 24, 20)
        body_lay.setSpacing(16)

        prompt_lbl = QLabel(self.translations.get("system_prompt_editor_text_label", "SYSTEM PROMPT DIRECTIVE"))
        prompt_lbl.setFont(self.f_label)
        prompt_lbl.setStyleSheet(f"color: {self._TEXT_S}; letter-spacing: 0.8px;")
        body_lay.addWidget(prompt_lbl)

        self.system_prompt_edit = QTextEdit()
        self.system_prompt_edit.setObjectName("SPEPromptEdit")
        self.system_prompt_edit.setFont(self.f_input)
        self.system_prompt_edit.setAcceptRichText(False)
        self.system_prompt_edit.setPlaceholderText(self.translations.get("system_prompt_editor_system_prompt_edit", "Write the system prompt here"))
        self.system_prompt_edit.setStyleSheet(self._s_input("SPEPromptEdit"))
        self.system_prompt_edit.setFixedHeight(250)
        body_lay.addWidget(self.system_prompt_edit)

        split_layout = QHBoxLayout()
        split_layout.setSpacing(16)

        order_col = QVBoxLayout()
        order_col.setSpacing(8)
        
        order_lbl = QLabel(self.translations.get("system_prompt_editor_component_label", "PROMPT CONSTRUCT ORDER  (Drag & Drop to Reorder)"))
        order_lbl.setFont(self.f_label)
        order_lbl.setStyleSheet(f"color: {self._TEXT_S}; letter-spacing: 0.8px;")
        order_col.addWidget(order_lbl)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("SPEListWidget")
        self.list_widget.setFont(self.f_input)
        self.list_widget.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.list_widget.setStyleSheet(
            f"QListWidget#SPEListWidget {{"
            f"  background-color: {self._SURF2};"
            f"  border: 1px solid {self._BORDER};"
            f"  border-radius: 8px;"
            f"  padding: 6px;"
            f"  outline: none;"
            f"}}"
            f"QListWidget#SPEListWidget::item {{"
            f"  background-color: {self._SURF3};"
            f"  border: 1px solid {self._BORDER};"
            f"  border-radius: 6px;"
            f"  margin: 4px;"
            f"  padding: 10px 14px;"
            f"  color: {self._TEXT};"
            f"}}"
            f"QListWidget#SPEListWidget::item:hover {{"
            f"  background-color: {self._SURF1};"
            f"  border-color: {self._BORDER_M};"
            f"}}"
            f"QListWidget#SPEListWidget::item:selected {{"
            f"  background-color: {self._BLUE_MUT};"
            f"  border-color: {self._BLUE_GLO};"
            f"  color: {self._BLUE};"
            f"}}"
        )
        order_col.addWidget(self.list_widget)
        split_layout.addLayout(order_col, stretch=1)

        panel_col = QVBoxLayout()
        panel_col.setSpacing(8)

        panel_lbl = QLabel(self.translations.get("system_prompt_editor_panel_title", "PRESET CONTROL PANEL"))
        panel_lbl.setFont(self.f_label)
        panel_lbl.setStyleSheet(f"color: {self._TEXT_S}; letter-spacing: 0.8px;")
        panel_col.addWidget(panel_lbl)

        control_panel = QFrame()
        control_panel.setObjectName("SPEControlPanel")
        control_panel.setStyleSheet(
            f"QFrame#SPEControlPanel {{"
            f"  background-color: {self._SURF1};"
            f"  border-radius: 10px;"
            f"  border: 1px solid {self._BORDER};"
            f"}}"
        )
        control_lay = QVBoxLayout(control_panel)
        control_lay.setContentsMargins(16, 16, 16, 16)
        control_lay.setSpacing(16)

        combo_lay = QVBoxLayout()
        combo_lay.setSpacing(6)
        
        preset_lbl = QLabel(self.translations.get("system_prompt_editor_presets", "Presets"))
        preset_lbl.setFont(self.f_label)
        preset_lbl.setStyleSheet("border: none; background: transparent; color: #6F6B63;")
        combo_lay.addWidget(preset_lbl)

        self.preset_combo = QComboBox()
        self.preset_combo.setObjectName("SPEPresetCombo")
        self.preset_combo.setFixedHeight(40)
        self.preset_combo.setFont(self.f_input)
        self.preset_combo.setStyleSheet(
            f"QComboBox#SPEPresetCombo {{"
            f"  background-color: {self._SURF2};"
            f"  color: {self._TEXT};"
            f"  border: 1px solid {self._BORDER};"
            f"  border-radius: 6px;"
            f"  padding-left: 12px;"
            f"}}"
            f"QComboBox#SPEPresetCombo:hover {{"
            f"  border-color: {self._BORDER_M};"
            f"}}"
            f"QComboBox#SPEPresetCombo::drop-down {{"
            f"  border: none;"
            f"  width: 24px;"
            f"}}"
            f"QComboBox#SPEPresetCombo::down-arrow {{"
            f"  width: 0; height: 0;"
            f"  border-left: 4px solid transparent;"
            f"  border-right: 4px solid transparent;"
            f"  border-top: 5px solid {self._TEXT_S};"
            f"}}"
            f"QComboBox#SPEPresetCombo QAbstractItemView {{"
            f"  background-color: {self._SURF3};"
            f"  color: {self._TEXT};"
            f"  border: 1px solid {self._BORDER_M};"
            f"  border-radius: 6px;"
            f"  padding: 4px;"
            f"  outline: none;"
            f"  selection-background-color: {self._SURF2};"
            f"}}"
        )
        combo_lay.addWidget(self.preset_combo)
        control_lay.addLayout(combo_lay)

        actions_lay = QVBoxLayout()
        actions_lay.setSpacing(10)

        self.new_preset_btn = QPushButton(self.translations.get("system_prompt_editor_new_preset", "New"))
        self.save_preset_button = QPushButton(self.translations.get("system_prompt_editor_save_preset", "Save"))
        self.delete_preset_btn = QPushButton(self.translations.get("system_prompt_editor_delete_preset", "Delete"))
        self.reset_button = QPushButton(self.translations.get("system_prompt_editor_default_btn", "Reset Default"))

        btn_action_style = (
            f"QPushButton {{"
            f"  background-color: {self._SURF2};"
            f"  color: {self._TEXT};"
            f"  border: 1px solid {self._BORDER};"
            f"  border-radius: 6px;"
            f"  height: 36px;"
            f"  font-family: 'Inter Tight Medium';"
            f"}}"
            f"QPushButton:hover {{"
            f"  background-color: {self._SURF3};"
            f"  border-color: {self._BORDER_M};"
            f"}}"
        )

        for btn in (self.new_preset_btn, self.save_preset_button, self.reset_button):
            btn.setFont(self.f_btn)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setStyleSheet(btn_action_style)

        self.delete_preset_btn.setFont(self.f_btn)
        self.delete_preset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_preset_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.delete_preset_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: transparent;"
            f"  color: {self._DANGER};"
            f"  border: 1px solid {self._DNG_GLO};"
            f"  border-radius: 6px;"
            f"  height: 36px;"
            f"  font-family: 'Inter Tight Medium';"
            f"}}"
            f"QPushButton:hover {{"
            f"  background-color: {self._DNG_MUT};"
            f"  border-color: rgba(196,64,64,0.45);"
            f"  color: #EE7777;"
            f"}}"
        )

        h_row1 = QHBoxLayout()
        h_row1.setSpacing(10)
        h_row1.addWidget(self.new_preset_btn, 1)
        h_row1.addWidget(self.save_preset_button, 1)
        actions_lay.addLayout(h_row1)

        actions_lay.addWidget(self.delete_preset_btn)

        sep_line = QFrame()
        sep_line.setFrameShape(QFrame.Shape.HLine)
        sep_line.setStyleSheet(f"border-top: 1px solid {self._BORDER}; margin: 6px 0;")
        actions_lay.addWidget(sep_line)

        actions_lay.addWidget(self.reset_button)
        control_lay.addLayout(actions_lay)
        control_lay.addStretch()

        panel_col.addWidget(control_panel)
        split_layout.addLayout(panel_col, stretch=1)

        body_lay.addLayout(split_layout)
        root.addWidget(body, 1)

        root.addWidget(self._build_footer())

    def _build_toolbar(self):
        bar = QFrame()
        bar.setObjectName("SPEToolbar")
        bar.setFixedHeight(56)
        bar.setStyleSheet(
            "QFrame#SPEToolbar {"
            f"  background: {self._SURF1};"
            f"  border-bottom: 1px solid {self._BORDER};"
            "}"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(12)

        title_lbl = QLabel(self.translations.get("system_prompt_editor_header_title", "SYSTEM PROMPT ENGINE"))
        title_lbl.setFont(self.f_title)
        title_lbl.setStyleSheet(f"color: {self._TEXT};")

        sep = QFrame()
        sep.setFixedSize(1, 24)
        sep.setStyleSheet(f"background: {self._BORDER};")

        sub_lbl = QLabel(self.translations.get("system_prompt_editor_subtitle", "CONSTRUCTS & PRESETS"))
        sub_lbl.setFont(self.f_label)
        sub_lbl.setStyleSheet(f"color: {self._TEXT_S}; letter-spacing: 1.1px;")

        lay.addWidget(title_lbl)
        lay.addWidget(sep)
        lay.addWidget(sub_lbl)
        lay.addStretch()
        return bar

    def _build_footer(self):
        bar = QFrame()
        bar.setObjectName("SPEFooter")
        bar.setFixedHeight(64)
        bar.setStyleSheet(
            "QFrame#SPEFooter {"
            f"  background: {self._SURF1};"
            f"  border-top: 1px solid {self._BORDER};"
            "}"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 24, 0)
        lay.setSpacing(12)

        lay.addStretch()

        btn_close = QPushButton(self.translations.get("personas_editor_close", "CLOSE"))
        btn_close.setObjectName("SPEBtnClose")
        btn_close.setFixedSize(140, 36)
        btn_close.setFont(self.f_btn)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(
            f"QPushButton#SPEBtnClose {{"
            f"  background: {self._ACC_MUT};"
            f"  border: 1px solid {self._ACC_GLO};"
            f"  border-radius: 6px;"
            f"  color: {self._ACCENT};"
            f"  letter-spacing: 0.5px;"
            f"}}"
            f"QPushButton#SPEBtnClose:hover {{"
            f"  background: rgba(196,154,56,0.27);"
            f"  border-color: rgba(196,154,56,0.52);"
            f"  color: {self._ACC_BRT};"
            f"}}"
        )
        btn_close.clicked.connect(self.close)
        lay.addWidget(btn_close)

        return bar

    def _s_input(self, name):
        return (
            f"QTextEdit#{name} {{"
            f"  background: {self._SURF2};"
            f"  border: 1px solid {self._BORDER};"
            f"  border-radius: 8px;"
            f"  color: {self._TEXT};"
            f"  padding: 12px 14px;"
            f"  selection-background-color: {self._BLUE_MUT};"
            f"  line-height: 1.4;"
            f"}}"
            f"QTextEdit#{name}:focus {{"
            f"  border-color: {self._BORDER_M};"
            f"  background: {self._SURF3};"
            f"}}"
        )

    def _setup_logic(self):
        self.reset_button.clicked.connect(self._reset_to_default)
        self.save_preset_button.clicked.connect(self._save_current_preset)
        self.new_preset_btn.clicked.connect(self._create_new_preset)
        self.delete_preset_btn.clicked.connect(self._delete_current_preset)
        self.preset_combo.currentTextChanged.connect(self._apply_current_preset)

    def _load_presets(self):
        return self.configuration_settings.get_all_presets()

    def _update_preset_combo(self):
        presets = self.configuration_settings.get_user_data("presets") or {}
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        for name in sorted(presets.keys()):
            self.preset_combo.addItem(name)
        self.preset_combo.blockSignals(False)

    def _apply_current_preset(self):
        presets = self.configuration_settings.get_user_data("presets") or {}
        name = self.preset_combo.currentText()
        if name in presets:
            data = presets[name]
            self.system_prompt_edit.setPlainText(data.get("prompt", ""))
            self.list_widget.blockSignals(True)
            self.list_widget.clear()
            self.list_widget.addItems(data.get("order", []))
            self.list_widget.blockSignals(False)

    def _save_current_preset(self):
        presets = self.configuration_settings.get_user_data("presets") or {}
        name = self.preset_combo.currentText()
        if name in presets:
            presets[name] = {
                "prompt": self.system_prompt_edit.toPlainText(),
                "order": [self.list_widget.item(i).text() for i in range(self.list_widget.count())]
            }
            self.configuration_settings.update_preset(name, presets[name])

            sow_toast(
                parent=self.main_window,
                title=self.translations.get("system_prompt_editor_title", "Prompt Editor"),
                text=self.translations.get("preset_saved_successfully", "Preset saved successfully."),
                msg_type="success"
            )

    def _reset_to_default(self):
        self.system_prompt_edit.setPlainText("You are a {{char}}, you must answer as {{char}}.")
        self.list_widget.clear()
        self.list_widget.addItems([
            "System prompt",
            "Character's information",
            "Persona information",
            "Lorebook",
            "Story Summary",
            "Author's notes"
        ])
        
    def _create_new_preset(self):
        dialog = SowInputDialog(
            parent=self,
            title=self.translations.get("system_prompt_editor_new_preset", "New preset"),
            label=self.translations.get("system_prompt_editor_preset_name", "Enter the preset name:"),
            placeholder="My Custom Prompt"
        )
        
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            name = dialog.get_text()
            if name:
                preset_data = {
                    "prompt": "You are {{char}}, you must answer as {{char}}.",
                    "order": [
                        "System prompt",
                        "Character's information",
                        "Persona information",
                        "Lorebook",
                        "Story Summary",
                        "Author's notes"
                    ]
                }
                self.configuration_settings.update_preset(name, preset_data)
                self._update_preset_combo()
                self.preset_combo.setCurrentText(name)
                
                sow_toast(
                    parent=self,
                    title=self.translations.get("system_prompt_editor_title", "Prompt Editor"),
                    text=self.translations.get("preset_saved_successfully", "Preset saved successfully."),
                    msg_type="success"
                )

    def _delete_current_preset(self):
        presets = self.configuration_settings.get_user_data("presets") or {}
        name = self.preset_combo.currentText()
        if name in presets:
            title = self.translations.get("system_prompt_editor_delete_preset_title", "Delete Preset")

            first_text = self.translations.get("system_prompt_editor_delete_preset_first", "Do you really want to remove the preset:")
            second_text = self.translations.get("system_prompt_editor_delete_preset_second", "This action cannot be canceled.")

            message_text = f"{first_text} '{name}'?\n{second_text}"

            dialog = SowConfirmDialog(
                parent=self.main_window,
                title=title,
                text=message_text,
                confirm_text="Delete",
                danger=True
            )

            if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                self.configuration_settings.delete_preset(name)
                self._update_preset_combo()
                self._apply_current_preset()

class DiscordGatewayDialog(QDialog):
    _BG       = "#0C0C10"
    _SURF1    = "#111117"
    _SURF2    = "#18181F"
    _SURF3    = "#1F1F27"
    _TEXT     = "#DEDAD2"
    _TEXT_S   = "#6F6B63"
    _BORDER   = "rgba(255,255,255,0.055)"
    _BORDER_M = "rgba(255,255,255,0.10)"
    
    _DISCORD  = "#5865F2"
    _DIS_MUT  = "rgba(88, 101, 242, 0.15)"
    _DIS_GLO  = "rgba(88, 101, 242, 0.35)"
    _DIS_HOV  = "rgba(88, 101, 242, 0.25)"
    _DIS_BRT  = "#737DF4"

    _DANGER   = "#F44336"
    _SUCCESS  = "#4CAF50"

    def __init__(self, translations, configuration_api, main_window, parent=None):
        super().__init__(parent)
        self.translations = translations
        self.configuration_api = configuration_api
        self.main_window = main_window

        self.setWindowTitle(self.translations.get("discord_gateway_title", "Discord Gateway"))
        self.setWindowIcon(QIcon("app/gui/icons/discord.png"))
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setMinimumSize(500, 380)

        self._init_fonts()
        self._apply_base_palette()
        self.setup_ui()
        self.update_status_ui()

    def _init_fonts(self):
        def mf(size, weight=QFont.Weight.Normal):
            f = QFont("Inter Tight", size, weight)
            f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            return f

        self.f_title = mf(13, QFont.Weight.Bold)
        self.f_label = mf(9,  QFont.Weight.Bold)
        self.f_desc  = mf(10, QFont.Weight.Medium)
        self.f_btn   = mf(10, QFont.Weight.DemiBold)
        
        self.f_token = mf(9, QFont.Weight.Medium)

    def _apply_base_palette(self):
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor(self._BG))
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_toolbar())
        root.addWidget(self._build_body(), 1)
        root.addWidget(self._build_footer())

    def _build_toolbar(self):
        bar = QFrame()
        bar.setObjectName("DGToolbar")
        bar.setFixedHeight(56)
        bar.setStyleSheet(
            "QFrame#DGToolbar {"
            f"  background: {self._SURF1};"
            f"  border-bottom: 1px solid {self._BORDER};"
            "}"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(12)

        title_lbl = QLabel(self.translations.get("discord_gateway_header", "DISCORD GATEWAY"))
        title_lbl.setFont(self.f_title)
        title_lbl.setStyleSheet(f"color: {self._TEXT}; letter-spacing: 1px;")

        sep = QFrame()
        sep.setFixedSize(1, 24)
        sep.setStyleSheet(f"background: {self._BORDER};")

        sub_lbl = QLabel(self.translations.get("discord_gateway_subtitle", "BOT INTEGRATION"))
        sub_lbl.setFont(self.f_label)
        sub_lbl.setStyleSheet(f"color: {self._TEXT_S}; letter-spacing: 1.1px;")

        lay.addWidget(title_lbl)
        lay.addWidget(sep)
        lay.addWidget(sub_lbl)
        lay.addStretch()

        return bar

    def _build_body(self):
        body = QFrame()
        body.setStyleSheet(f"background: {self._BG}; border: none;")
        lay = QVBoxLayout(body)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        info_label = QLabel(self.translations.get(
            "discord_info", 
            "Enter your Discord Bot Token to connect your currently active character to Discord. The bot will reply to messages in servers it has access to."
        ))
        info_label.setFont(self.f_desc)
        info_label.setStyleSheet(f"color: {self._TEXT_S};")
        info_label.setWordWrap(True)
        lay.addWidget(info_label)

        lay.addSpacing(8)

        token_lbl = QLabel(self.translations.get("discord_token_label", "BOT TOKEN"))
        token_lbl.setFont(self.f_label)
        token_lbl.setStyleSheet(f"color: {self._TEXT_S}; letter-spacing: 0.8px;")
        lay.addWidget(token_lbl)

        self.token_input = QLineEdit()
        self.token_input.setObjectName("DGTokenInput")
        self.token_input.setPlaceholderText("Paste your Discord Bot Token here...")
        self.token_input.setFont(self.f_token)
        self.token_input.setFixedHeight(38)
        self.token_input.setStyleSheet(
            f"QLineEdit#DGTokenInput {{"
            f"  background: {self._SURF2};"
            f"  border: 1px solid {self._BORDER};"
            f"  border-radius: 8px;"
            f"  color: {self._TEXT};"
            f"  padding: 0 12px;"
            f"  selection-background-color: {self._DIS_MUT};"
            f"}}"
            f"QLineEdit#DGTokenInput:focus {{"
            f"  border-color: {self._BORDER_M};"
            f"  background: {self._SURF3};"
            f"}}"
        )
        
        config_api = self.configuration_api.get_token("DISCORD_BOT_TOKEN")
        if config_api:
            self.token_input.setText(config_api)

        lay.addWidget(self.token_input)

        lay.addStretch()

        status_layout = QHBoxLayout()
        status_lbl = QLabel(self.translations.get("discord_gateway_status", "Current Status:"))
        status_lbl.setFont(self.f_desc)
        status_lbl.setStyleSheet(f"color: {self._TEXT_S};")
        
        self.status_badge = QLabel()
        self.status_badge.setFont(self.f_label)
        self.status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_badge.setFixedHeight(28)
        
        status_layout.addWidget(status_lbl)
        status_layout.addWidget(self.status_badge)
        status_layout.addStretch()
        
        lay.addLayout(status_layout)

        return body

    def _build_footer(self):
        bar = QFrame()
        bar.setObjectName("DGFooter")
        bar.setFixedHeight(64)
        bar.setStyleSheet(
            "QFrame#DGFooter {"
            f"  background: {self._SURF1};"
            f"  border-top: 1px solid {self._BORDER};"
            "}"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 24, 0)
        lay.setSpacing(12)

        self.stop_btn = QPushButton(self.translations.get("discord_stop_btn", "Stop Bot"))
        self.stop_btn.setObjectName("DGBtnStop")
        self.stop_btn.setFixedSize(120, 36)
        self.stop_btn.setFont(self.f_btn)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setStyleSheet(
            f"QPushButton#DGBtnStop {{ background: transparent; border: 1px solid {self._BORDER}; border-radius: 6px; color: {self._TEXT_S}; letter-spacing: 0.5px; }}"
            f"QPushButton#DGBtnStop:hover {{ background: rgba(244, 67, 54, 0.1); border-color: rgba(244, 67, 54, 0.3); color: {self._DANGER}; }}"
        )

        lay.addStretch()
        lay.addWidget(self.stop_btn)

        self.start_btn = QPushButton(self.translations.get("discord_start_btn", "Start Bot"))
        self.start_btn.setObjectName("DGBtnStart")
        self.start_btn.setFixedSize(140, 36)
        self.start_btn.setFont(self.f_btn)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setStyleSheet(
            f"QPushButton#DGBtnStart {{ background: {self._DIS_MUT}; border: 1px solid {self._DIS_GLO}; border-radius: 6px; color: {self._DISCORD}; letter-spacing: 0.5px; }}"
            f"QPushButton#DGBtnStart:hover {{ background: {self._DIS_HOV}; border-color: {self._DISCORD}; color: {self._DIS_BRT}; }}"
        )

        lay.addWidget(self.start_btn)

        self.start_btn.clicked.connect(self.on_start)
        self.stop_btn.clicked.connect(self.on_stop)

        return bar

    def update_status_ui(self):
        if self.main_window.discord_manager and self.main_window.discord_manager.is_running:
            self.status_badge.setText(f"  {self.translations.get('discord_status_running', 'RUNNING')}  ")
            self.status_badge.setStyleSheet(
                f"background: rgba(76, 175, 80, 0.15);"
                f"color: {self._SUCCESS};"
                f"border: 1px solid rgba(76, 175, 80, 0.3);"
                f"border-radius: 6px;"
            )
        else:
            self.status_badge.setText(f"  {self.translations.get('discord_status_stopped', 'STOPPED')}  ")
            self.status_badge.setStyleSheet(
                f"background: rgba(244, 67, 54, 0.15);"
                f"color: {self._DANGER};"
                f"border: 1px solid rgba(244, 67, 54, 0.3);"
                f"border-radius: 6px;"
            )

    def save_token(self):
        from app.configuration.configuration import ConfigurationAPI
        api = ConfigurationAPI()
        tokens = api.load_configuration()
        tokens["DISCORD_BOT_TOKEN"] = self.token_input.text()
        api.save_configuration_edit(tokens)

    def on_start(self):
        self.save_token()
        if self.main_window.discord_manager:
            self.main_window.discord_manager.start_bot()
            self.update_status_ui()

    def on_stop(self):
        if self.main_window.discord_manager:
            asyncio.create_task(self.main_window.discord_manager.stop_bot())
            self.update_status_ui()

_TRIGGER_KEYS   = ["keyword", "semantic", "always_on", "random", "chain", "range"]
_TRIGGER_ABBR   = {
    "keyword":   "🔑",
    "semantic":  "🧠",
    "always_on": "📌",
    "random":    "🎲",
    "chain":     "🔗",
    "range":     "🎬",
}

class LorebookEditorDialog(QDialog):
    _BG       = "#0C0C10"
    _SURF1    = "#111117"
    _SURF2    = "#18181F"
    _SURF3    = "#1F1F27"
    _SURF4    = "#26262F"
    _ACCENT   = "#C49A38"
    _ACC_MUT  = "rgba(196,154,56,0.15)"
    _ACC_GLO  = "rgba(196,154,56,0.32)"
    _ACC_BRT  = "#E2B34C"
    _TEXT     = "#DEDAD2"
    _TEXT_S   = "#6F6B63"
    _TEXT_D   = "#38352F"
    _BORDER   = "rgba(255,255,255,0.055)"
    _BORDER_M = "rgba(255,255,255,0.10)"
    _DANGER   = "#C44040"
    _DNG_MUT  = "rgba(196,64,64,0.13)"
    _DNG_GLO  = "rgba(196,64,64,0.28)"
 
    def __init__(self, translations, configuration_settings, main_window, parent=None):
        super().__init__(parent)
        self.translations            = translations
        self.configuration_settings  = configuration_settings
        self.main_window             = main_window
 
        self.setWindowTitle(self.translations.get("lorebook_engine_title", "Lorebook Engine"))
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowMinMaxButtonsHint
        )
        self.setMinimumSize(960, 640)
        self.resize(1120, 720)
 
        self.lorebooks              = {}
        self.current_lorebook_name  = None
        self.current_entry_index    = -1
        self.is_programmatic_change = False

        self.tokenizer = tiktoken.get_encoding("cl100k_base")

        self._trigger_labels = [
            self.translations.get("lorebook_trig_keyword", "Keywords"),
            self.translations.get("lorebook_trig_semantic", "Semantic"),
            self.translations.get("lorebook_trig_always_on", "Always On"),
            self.translations.get("lorebook_trig_random", "Random"),
            self.translations.get("lorebook_trig_chain", "Chain"),
            self.translations.get("lorebook_trig_scenario", "Scenario")
        ]

        self._trig_card_titles = {
            0: self.translations.get("lorebook_trig_title_keyword", "KEYWORD MATCHING"),
            1: self.translations.get("lorebook_trig_title_semantic", "SEMANTIC SITUATION"),
            2: self.translations.get("lorebook_trig_title_always_on", "ALWAYS ACTIVE"),
            3: self.translations.get("lorebook_trig_title_random", "RANDOM TRIGGER"),
            4: self.translations.get("lorebook_trig_title_chain", "CHAIN DEPENDENCY"),
            5: self.translations.get("lorebook_trig_title_scenario", "SCENARIO RANGE"),
        }
 
        self._init_fonts()
        self._apply_base_palette()
        self.setup_ui()
        self.load_lorebooks()
        self.update_lorebook_combo()
        if self.lorebook_combo.count() > 0:
            self.apply_current_lorebook()
 
    def _init_fonts(self):
        def mf(size, weight=QFont.Weight.Normal):
            f = QFont("Inter Tight", size, weight)
            f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            return f
 
        self.f_title = mf(13, QFont.Weight.Bold)
        self.f_head  = mf(10, QFont.Weight.Medium)
        self.f_label = mf(8,  QFont.Weight.Bold)
        self.f_input = mf(10)
        self.f_btn   = mf(10, QFont.Weight.DemiBold)
        self.f_entry = mf(10, QFont.Weight.Medium)
 
    def _apply_base_palette(self):
        pal = self.palette()
        pal.setColor(QtGui.QPalette.ColorRole.Window, QColor(self._BG))
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
 
        root.addWidget(self._build_toolbar())
        root.addWidget(self._build_body(), 1)
        root.addWidget(self._build_footer())
 
        self._connect_signals()

    def _build_toolbar(self):
        bar = QFrame()
        bar.setObjectName("LBToolbar")
        bar.setFixedHeight(54)
        bar.setStyleSheet(
            "QFrame#LBToolbar {"
            f"  background: {self._SURF1};"
            f"  border-bottom: 1px solid {self._BORDER};"
            "}"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(8)
 
        title_lbl = QLabel(self.translations.get("lorebook_engine_title", "Lorebook Engine"))
        title_lbl.setFont(self.f_title)
        title_lbl.setStyleSheet(f"color: {self._TEXT};")
 
        sep = self._vsep(28)
 
        lib_lbl = QLabel(self.translations.get("lorebook_library_label", "LIBRARY"))
        lib_lbl.setFont(self.f_label)
        lib_lbl.setStyleSheet(f"color: {self._TEXT_S}; letter-spacing: 1.1px;")
 
        self.lorebook_combo = QComboBox()
        self.lorebook_combo.setObjectName("LBLorebookCombo")
        self.lorebook_combo.setFixedSize(210, 32)
        self.lorebook_combo.setFont(self.f_input)
        self.lorebook_combo.setStyleSheet(self._s_combo("LBLorebookCombo"))
 
        self.btn_add_lb    = self._icon_btn("app/gui/icons/plus.png", self.translations.get("lorebook_editor_new_lorebook", "New Lorebook"),       obj="LBBtnAddLB")
        self.btn_rename_lb = self._icon_btn("app/gui/icons/edit.png", self.translations.get("lorebook_rename_btn", "Rename"),             obj="LBBtnRenameLB")
        self.btn_del_lb    = self._icon_btn("app/gui/icons/bin.png",  self.translations.get("lorebook_editor_delete_lorebook", "Delete Lorebook"),    obj="LBBtnDelLB", danger=True)
 
        lay.addWidget(title_lbl)
        lay.addWidget(sep)
        lay.addWidget(lib_lbl)
        lay.addWidget(self.lorebook_combo)
        lay.addWidget(self.btn_add_lb)
        lay.addWidget(self.btn_rename_lb)
        lay.addWidget(self.btn_del_lb)
        lay.addStretch()
        return bar

    def _build_body(self):
        splitter = QtWidgets.QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("LBSplitter")
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(
            "QSplitter#LBSplitter::handle {"
            f"  background: {self._BORDER};"
            "}"
        )
        splitter.addWidget(self._build_sidebar())
        splitter.addWidget(self._build_editor())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([275, 845])
        return splitter

    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("LBSidebar")
        sidebar.setFixedWidth(275)
        sidebar.setStyleSheet(
            "QFrame#LBSidebar {"
            f"  background: {self._SURF1};"
            "  border: none;"
            "}"
        )
        lay = QVBoxLayout(sidebar)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)
 
        self.search_bar = QLineEdit()
        self.search_bar.setObjectName("LBSearchBar")
        self.search_bar.setPlaceholderText(self.translations.get("lorebook_filter_placeholder", "Filter entries..."))
        self.search_bar.setFixedHeight(32)
        self.search_bar.setFont(self.f_input)
        self.search_bar.setStyleSheet(self._s_lineedit("LBSearchBar"))
        lay.addWidget(self.search_bar)
 
        self.lbl_count = QLabel("0 " + self.translations.get("lorebook_editor_suffix_entries", "entries"))
        self.lbl_count.setObjectName("LBCount")
        self.lbl_count.setFont(self.f_label)
        self.lbl_count.setStyleSheet(
            f"QLabel#LBCount {{ color: {self._TEXT_D}; padding-left: 2px; }}"
        )
        lay.addWidget(self.lbl_count)
 
        self.entry_list = QListWidget()
        self.entry_list.setObjectName("LBEntryList")
        self.entry_list.setFont(self.f_entry)
        self.entry_list.setStyleSheet(self._s_list())
        self.entry_list.setSpacing(2)
        self.entry_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        lay.addWidget(self.entry_list, 1)
 
        self.btn_new_entry = QPushButton(self.translations.get("lorebook_editor_add_entry", "+ New Entry"))
        self.btn_new_entry.setObjectName("LBBtnNewEntry")
        self.btn_new_entry.setFixedHeight(36)
        self.btn_new_entry.setFont(self.f_btn)
        self.btn_new_entry.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new_entry.setStyleSheet(self._s_action_btn("LBBtnNewEntry"))
        lay.addWidget(self.btn_new_entry)
        return sidebar

    def _build_editor(self):
        host = QFrame()
        host.setObjectName("LBEditorHost")
        host.setStyleSheet(
            "QFrame#LBEditorHost {"
            f"  background: {self._BG};"
            "  border: none;"
            "}"
        )
        host_lay = QVBoxLayout(host)
        host_lay.setContentsMargins(0, 0, 0, 0)
        host_lay.setSpacing(0)

        self.empty_state = QWidget()
        self.empty_state.setObjectName("LBEmptyState")
        es_lay = QVBoxLayout(self.empty_state)
        es_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        es_txt = QLabel(self.translations.get("lorebook_empty_state", "Select an entry or create a new one to begin editing."))
        es_txt.setObjectName("LBEmptyLabel")
        es_txt.setFont(self.f_head)
        es_txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        es_txt.setStyleSheet(f"QLabel#LBEmptyLabel {{ color: {self._TEXT_D}; }}")
        es_lay.addWidget(es_txt)
        host_lay.addWidget(self.empty_state, 1)

        self.form_widget = QWidget()
        self.form_widget.setObjectName("LBForm")
        self.form_widget.setVisible(False)
        form_lay = QVBoxLayout(self.form_widget)
        form_lay.setContentsMargins(22, 16, 22, 12)
        form_lay.setSpacing(0)

        row_a = QHBoxLayout()
        row_a.setSpacing(12)
 
        self.input_name = QLineEdit()
        self.input_name.setObjectName("LBInputName")
        self.input_name.setPlaceholderText(self.translations.get("lorebook_entry_name_placeholder", "Entry name..."))
        self.input_name.setFixedHeight(34)
        self.input_name.setFont(self.f_input)
        self.input_name.setStyleSheet(self._s_lineedit("LBInputName"))
 
        self.combo_type = QComboBox()
        self.combo_type.setObjectName("LBComboType")
        self.combo_type.addItems(self._trigger_labels)
        self.combo_type.setFixedHeight(34)
        self.combo_type.setFixedWidth(145)
        self.combo_type.setFont(self.f_input)
        self.combo_type.setStyleSheet(self._s_combo("LBComboType"))
 
        self.combo_inj = QComboBox()
        self.combo_inj.setObjectName("LBComboInj")
        self.combo_inj.addItems([
            self.translations.get("lorebook_injection_passive", "Passive"), 
            self.translations.get("lorebook_injection_active", "Active")
        ])
        self.combo_inj.setFixedHeight(34)
        self.combo_inj.setFixedWidth(130)
        self.combo_inj.setFont(self.f_input)
        self.combo_inj.setStyleSheet(self._s_combo("LBComboInj"))
 
        row_a.addLayout(self._labeled(self.translations.get("lorebook_editor_entry_name", "ENTRY NAME"),   self.input_name),  1)
        row_a.addLayout(self._labeled(self.translations.get("lorebook_trigger_type_label", "TRIGGER TYPE"), self.combo_type),  0)
        row_a.addLayout(self._labeled(self.translations.get("lorebook_injection_label", "INJECTION"),    self.combo_inj),   0)
        form_lay.addLayout(row_a)
        form_lay.addSpacing(12)

        self.trigger_card = QFrame()
        self.trigger_card.setObjectName("LBTrigCard")
        self.trigger_card.setStyleSheet(
            "QFrame#LBTrigCard {"
            f"  background: {self._SURF2};"
            f"  border: 1px solid {self._BORDER};"
            "  border-radius: 8px;"
            "}"
        )
        trig_lay = QVBoxLayout(self.trigger_card)
        trig_lay.setContentsMargins(14, 10, 14, 10)
        trig_lay.setSpacing(8)
 
        self.lbl_trig_title = QLabel(self.translations.get("lorebook_trigger_config_label", "TRIGGER CONFIGURATION"))
        self.lbl_trig_title.setObjectName("LBTrigTitle")
        self.lbl_trig_title.setFont(self.f_label)
        self.lbl_trig_title.setStyleSheet(
            f"QLabel#LBTrigTitle {{ color: {self._TEXT_S}; letter-spacing: 1px; }}"
        )
        trig_lay.addWidget(self.lbl_trig_title)
 
        self.stack_triggers = QtWidgets.QStackedWidget()
        self.stack_triggers.setObjectName("LBStack")
        self.stack_triggers.setStyleSheet(
            "QStackedWidget#LBStack { background: transparent; border: none; }"
        )
        self._init_stack_pages()
        trig_lay.addWidget(self.stack_triggers)
 
        form_lay.addWidget(self.trigger_card)
        form_lay.addSpacing(12)

        self.input_content = QTextEdit()
        self.input_content.setObjectName("LBInputContent")
        self.input_content.setFont(self.f_input)
        self.input_content.setMinimumHeight(145)
        self.input_content.setStyleSheet(self._s_textedit("LBInputContent"))
        form_lay.addLayout(self._labeled(self.translations.get("lorebook_content_label", "LORE CONTENT  /  SCENARIO TEXT"), self.input_content))
        form_lay.addSpacing(12)

        props = QFrame()
        props.setObjectName("LBPropsCard")
        props.setStyleSheet(
            "QFrame#LBPropsCard {"
            f"  background: {self._SURF1};"
            f"  border: 1px solid {self._BORDER};"
            "  border-radius: 8px;"
            "}"
        )
        props_lay = QHBoxLayout(props)
        props_lay.setContentsMargins(16, 10, 16, 10)
        props_lay.setSpacing(0)
 
        self.spin_sticky = QSpinBox(); self.spin_sticky.setObjectName("LBSpinSticky"); self.spin_sticky.setRange(0, 99)
        self.spin_cd     = QSpinBox(); self.spin_cd.setObjectName("LBSpinCD");         self.spin_cd.setRange(0, 999)
        self.spin_delay  = QSpinBox(); self.spin_delay.setObjectName("LBSpinDelay");   self.spin_delay.setRange(0, 999)
        self.spin_prob   = QSpinBox(); self.spin_prob.setObjectName("LBSpinProb");     self.spin_prob.setRange(0, 100); self.spin_prob.setValue(100); self.spin_prob.setSuffix(" %")
 
        for sp in (self.spin_sticky, self.spin_cd, self.spin_delay, self.spin_prob):
            sp.setFixedSize(80, 28)
            sp.setFont(self.f_input)
            sp.setStyleSheet(self._s_spin(sp.objectName()))
 
        props_lay.addLayout(self._spin_group(self.translations.get("lorebook_sticky_label", "STICKY"),      self.spin_sticky, self.translations.get("lorebook_editor_suffix", "msgs")))
        props_lay.addWidget(self._vsep(22))
        props_lay.addLayout(self._spin_group(self.translations.get("lorebook_cooldown_label", "COOLDOWN"),    self.spin_cd,     self.translations.get("lorebook_editor_suffix", "msgs")))
        props_lay.addWidget(self._vsep(22))
        props_lay.addLayout(self._spin_group(self.translations.get("lorebook_delay_label", "DELAY"),       self.spin_delay,  self.translations.get("lorebook_editor_suffix", "msgs")))
        props_lay.addWidget(self._vsep(22))
        props_lay.addLayout(self._spin_group(self.translations.get("lorebook_probability_label", "PROBABILITY"), self.spin_prob,   ""))
        props_lay.addStretch()
 
        self.btn_del_entry = QPushButton(self.translations.get("lorebook_editor_delete_entry", "Delete Entry"))
        self.btn_del_entry.setObjectName("LBBtnDelEntry")
        self.btn_del_entry.setFixedSize(114, 30)
        self.btn_del_entry.setFont(self.f_btn)
        self.btn_del_entry.setStyleSheet(self._s_danger_btn("LBBtnDelEntry"))
        props_lay.addWidget(self.btn_del_entry, 0, Qt.AlignmentFlag.AlignVCenter)
 
        form_lay.addWidget(props)
        form_lay.addStretch()
 
        host_lay.addWidget(self.form_widget, 1)
        return host

    def _build_footer(self):
        bar = QFrame()
        bar.setObjectName("LBFooter")
        bar.setFixedHeight(50)
        bar.setStyleSheet(
            "QFrame#LBFooter {"
            f"  background: {self._SURF1};"
            f"  border-top: 1px solid {self._BORDER};"
            "}"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(8)
 
        depth_lbl = QLabel(self.translations.get("lorebook_editor_scan_depth", "SCAN DEPTH"))
        depth_lbl.setFont(self.f_label)
        depth_lbl.setStyleSheet(f"color: {self._TEXT_S}; letter-spacing: 1px;")
 
        self.depth_combo = QComboBox()
        self.depth_combo.setObjectName("LBDepthCombo")
        self.depth_combo.addItems([f"{i} {self.translations.get('lorebook_depth_suffix', 'messages')}" for i in range(1, 21)])
        self.depth_combo.setFixedSize(128, 30)
        self.depth_combo.setFont(self.f_input)
        self.depth_combo.setStyleSheet(self._s_combo("LBDepthCombo"))

        self.token_counter_lbl = QLabel("Tokens: 0")
        self.token_counter_lbl.setFont(self.f_label)
        self.token_counter_lbl.setStyleSheet(f"color: {self._TEXT_S}; margin-left: 12px; background: transparent; border: none;")
 
        self.btn_import = self._text_icon_btn("app/gui/icons/import.png", self.translations.get("lorebook_editor_import_lorebook", "Import JSON"), "LBBtnImport")
        self.btn_export = self._text_icon_btn("app/gui/icons/export.png", self.translations.get("lorebook_editor_export_lorebook", "Export JSON"), "LBBtnExport")
 
        self.btn_save_all = QPushButton(self.translations.get("lorebook_apply_changes_btn", "APPLY CHANGES"))
        self.btn_save_all.setObjectName("LBBtnSave")
        self.btn_save_all.setFixedSize(150, 32)
        self.btn_save_all.setFont(self.f_btn)
        self.btn_save_all.setStyleSheet(self._s_accent_btn("LBBtnSave"))
 
        lay.addWidget(depth_lbl)
        lay.addWidget(self.depth_combo)
        lay.addWidget(self.token_counter_lbl)
        lay.addStretch()
        lay.addWidget(self.btn_import)
        lay.addWidget(self.btn_export)
        lay.addSpacing(6)
        lay.addWidget(self.btn_save_all)
        return bar

    def _init_stack_pages(self):
        # Page 0 — Keywords
        pg0 = QWidget(); pg0.setObjectName("LBPgKeywords")
        l0 = QHBoxLayout(pg0); l0.setContentsMargins(0,0,0,0); l0.setSpacing(12)
        self.input_keys = QLineEdit(); self.input_keys.setObjectName("LBInputKeys")
        self.input_keys.setPlaceholderText(self.translations.get("lorebook_include_keywords_placeholder", "dragon, ancient, fire...")); self.input_keys.setFixedHeight(32)
        self.input_keys.setFont(self.f_input); self.input_keys.setStyleSheet(self._s_lineedit("LBInputKeys"))
        self.input_exclude = QLineEdit(); self.input_exclude.setObjectName("LBInputExclude")
        self.input_exclude.setPlaceholderText(self.translations.get("lorebook_exclude_keywords_placeholder", "exception words...")); self.input_exclude.setFixedHeight(32)
        self.input_exclude.setFont(self.f_input); self.input_exclude.setStyleSheet(self._s_lineedit("LBInputExclude"))
        l0.addLayout(self._labeled(self.translations.get("lorebook_include_keywords_label", "INCLUDE KEYWORDS  (comma-separated)"), self.input_keys))
        l0.addLayout(self._labeled(self.translations.get("lorebook_exclude_keywords_label", "EXCLUDE KEYWORDS  (comma-separated)"), self.input_exclude))
 
        # Page 1 — Semantic
        pg1 = QWidget(); pg1.setObjectName("LBPgSemantic")
        l1 = QVBoxLayout(pg1); l1.setContentsMargins(0,0,0,0)
        self.input_semantic = QTextEdit(); self.input_semantic.setObjectName("LBInputSemantic")
        self.input_semantic.setMaximumHeight(60)
        self.input_semantic.setPlaceholderText(self.translations.get("lorebook_semantic_placeholder", "Describe the scene or situation for the AI to recognize..."))
        self.input_semantic.setFont(self.f_input); self.input_semantic.setStyleSheet(self._s_textedit("LBInputSemantic"))
        l1.addLayout(self._labeled(self.translations.get("lorebook_semantic_label", "SCENE DESCRIPTION FOR AI SEMANTIC MATCH"), self.input_semantic))
 
        # Page 2 — Always On
        pg2 = QWidget(); pg2.setObjectName("LBPgAlwaysOn")
        l2 = QHBoxLayout(pg2); l2.setContentsMargins(0,0,0,0)
        lbl2 = QLabel(self.translations.get("lorebook_always_on_hint", "Always active — injected into every context window, every turn."))
        lbl2.setFont(self.f_input); lbl2.setStyleSheet(f"color: {self._TEXT_S}; font-style: italic;")
        l2.addWidget(lbl2)
 
        # Page 3 — Random
        pg3 = QWidget(); pg3.setObjectName("LBPgRandom")
        l3 = QHBoxLayout(pg3); l3.setContentsMargins(0,0,0,0)
        lbl3 = QLabel(self.translations.get("lorebook_random_hint", "Fires randomly each turn, controlled by the Probability setting below."))
        lbl3.setFont(self.f_input); lbl3.setStyleSheet(f"color: {self._TEXT_S}; font-style: italic;")
        l3.addWidget(lbl3)
 
        # Page 4 — Chain
        pg4 = QWidget(); pg4.setObjectName("LBPgChain")
        l4 = QHBoxLayout(pg4); l4.setContentsMargins(0,0,0,0); l4.setSpacing(12)
        self.spin_chain = QSpinBox(); self.spin_chain.setObjectName("LBSpinChain")
        self.spin_chain.setRange(-1, 9999); self.spin_chain.setValue(-1)
        self.spin_chain.setSpecialValueText(self.translations.get("lorebook_any_value", "any  (-1)"))
        self.spin_chain_del = QSpinBox(); self.spin_chain_del.setObjectName("LBSpinChainDel")
        self.spin_chain_del.setRange(0, 999)
        for s in (self.spin_chain, self.spin_chain_del):
            s.setFixedHeight(32); s.setFont(self.f_input); s.setStyleSheet(self._s_spin(s.objectName()))
        l4.addLayout(self._labeled(self.translations.get("lorebook_parent_uid_label", "PARENT ENTRY UID  (-1 = any)"),          self.spin_chain))
        l4.addLayout(self._labeled(self.translations.get("lorebook_chain_delay_label", "CHAIN DELAY  (messages after parent)"),   self.spin_chain_del))
 
        # Page 5 — Scenario range
        pg5 = QWidget(); pg5.setObjectName("LBPgScenario")
        l5 = QHBoxLayout(pg5); l5.setContentsMargins(0,0,0,0); l5.setSpacing(12)
        self.spin_min = QSpinBox(); self.spin_min.setObjectName("LBSpinMin"); self.spin_min.setRange(0, 99999)
        self.spin_max = QSpinBox(); self.spin_max.setObjectName("LBSpinMax"); self.spin_max.setRange(0, 99999); self.spin_max.setValue(9999)
        for s in (self.spin_min, self.spin_max):
            s.setFixedHeight(32); s.setFont(self.f_input); s.setStyleSheet(self._s_spin(s.objectName()))
        l5.addLayout(self._labeled(self.translations.get("lorebook_first_msg_label", "FIRST MESSAGE  (inclusive)"), self.spin_min))
        l5.addLayout(self._labeled(self.translations.get("lorebook_last_msg_label", "LAST MESSAGE  (inclusive)"),  self.spin_max))
 
        for pg in (pg0, pg1, pg2, pg3, pg4, pg5):
            self.stack_triggers.addWidget(pg)

    def _connect_signals(self):
        self.lorebook_combo.currentIndexChanged.connect(self.apply_current_lorebook)
        self.entry_list.itemClicked.connect(self.select_entry)
        self.search_bar.textChanged.connect(self.populate_entry_list)
        self.btn_new_entry.clicked.connect(self.add_entry)
        self.btn_del_entry.clicked.connect(self.delete_entry)
        self.btn_save_all.clicked.connect(self.global_save)
        self.btn_add_lb.clicked.connect(self.create_lorebook)
        self.btn_rename_lb.clicked.connect(self.rename_lorebook_action)
        self.btn_del_lb.clicked.connect(self.delete_lorebook_action)
        self.btn_import.clicked.connect(self.import_lorebook_action)
        self.btn_export.clicked.connect(self.export_lorebook_action)
        self.combo_type.currentIndexChanged.connect(self.on_type_changed)
 
        for w in (self.input_name, self.input_keys, self.input_exclude):
            w.textChanged.connect(self.save_current_entry_changes)
        for w in (self.input_content, self.input_semantic):
            w.textChanged.connect(self.save_current_entry_changes)
        self.combo_inj.currentIndexChanged.connect(self.save_current_entry_changes)
        for w in (self.spin_chain, self.spin_chain_del,
                  self.spin_min,   self.spin_max,
                  self.spin_sticky, self.spin_cd, self.spin_delay, self.spin_prob):
            w.valueChanged.connect(self.save_current_entry_changes)

    def _labeled(self, text, widget):
        v = QVBoxLayout(); v.setSpacing(4); v.setContentsMargins(0,0,0,0)
        lbl = QLabel(text); lbl.setFont(self.f_label)
        lbl.setStyleSheet(f"color: {self._TEXT_S}; letter-spacing: 0.7px;")
        v.addWidget(lbl); v.addWidget(widget)
        return v
 
    def _spin_group(self, label, spinbox, unit):
        v = QVBoxLayout(); v.setSpacing(4); v.setContentsMargins(0,0,16,0)
        lbl = QLabel(label); lbl.setFont(self.f_label)
        lbl.setStyleSheet(f"color: {self._TEXT_S}; letter-spacing: 0.7px;")
        row = QHBoxLayout(); row.setSpacing(4); row.addWidget(spinbox)
        if unit:
            u = QLabel(unit); u.setFont(self.f_label)
            u.setStyleSheet(f"color: {self._TEXT_D};"); row.addWidget(u)
        v.addWidget(lbl); v.addLayout(row)
        return v
 
    def _vsep(self, height=24):
        wrapper = QWidget(); wl = QHBoxLayout(wrapper); wl.setContentsMargins(8,0,8,0)
        s = QFrame(); s.setFixedSize(1, height)
        s.setStyleSheet(f"background: {self._BORDER};"); wl.addWidget(s)
        return wrapper
 
    def _icon_btn(self, path, tip, obj, danger=False):
        b = QPushButton(); b.setObjectName(obj)
        b.setFixedSize(32, 32)
        b.setIcon(QtGui.QIcon(path)); b.setIconSize(QtCore.QSize(14, 14))
        b.setToolTip(tip); b.setCursor(Qt.CursorShape.PointingHandCursor)
        if danger:
            b.setStyleSheet(
                f"QToolTip {{ background-color: {self._SURF3}; color: {self._TEXT}; border: 1px solid {self._BORDER_M}; border-radius: 6px; padding: 6px; }}"
                f"QPushButton#{obj}{{background:{self._DNG_MUT};border:1px solid rgba(196,64,64,0.18);border-radius:6px;}}"
                f"QPushButton#{obj}:hover{{background:{self._DNG_GLO};border-color:rgba(196,64,64,0.45);}}"
            )
        else:
            b.setStyleSheet(
                f"QToolTip {{ background-color: {self._SURF3}; color: {self._TEXT}; border: 1px solid {self._BORDER_M}; border-radius: 6px; padding: 6px; }}"
                f"QPushButton#{obj}{{background:{self._SURF2};border:1px solid {self._BORDER};border-radius:6px;}}"
                f"QPushButton#{obj}:hover{{background:{self._SURF3};border-color:{self._BORDER_M};}}"
            )
        return b
 
    def _text_icon_btn(self, path, text, obj):
        b = QPushButton(f"  {text}"); b.setObjectName(obj)
        b.setIcon(QtGui.QIcon(path)); b.setIconSize(QtCore.QSize(13, 13))
        b.setFixedHeight(32); b.setFont(self.f_btn)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setStyleSheet(
            f"QPushButton#{obj}{{background:transparent;border:1px solid {self._BORDER};"
            f"border-radius:6px;color:{self._TEXT_S};padding:0 12px;}}"
            f"QPushButton#{obj}:hover{{background:{self._SURF2};color:{self._TEXT};"
            f"border-color:{self._BORDER_M};}}"
        )
        return b

    def _s_lineedit(self, name):
        return (
            f"QLineEdit#{name}{{background:{self._SURF2};border:1px solid {self._BORDER};"
            f"border-radius:6px;color:{self._TEXT};padding:0 10px;selection-background-color:{self._ACC_MUT};}}"
            f"QLineEdit#{name}:focus{{border-color:{self._BORDER_M};background:{self._SURF3};}}"
        )
 
    def _s_textedit(self, name):
        return (
            f"QTextEdit#{name}{{background:{self._SURF2};border:1px solid {self._BORDER};"
            f"border-radius:8px;color:{self._TEXT};padding:8px 10px;selection-background-color:{self._ACC_MUT};}}"
            f"QTextEdit#{name}:focus{{border-color:{self._BORDER_M};background:{self._SURF3};}}"
        )
 
    def _s_combo(self, name):
        return (
            f"QComboBox#{name}{{background:{self._SURF2};border:1px solid {self._BORDER};"
            f"border-radius:6px;color:{self._TEXT};padding:0 10px;}}"
            f"QComboBox#{name}:hover{{border-color:{self._BORDER_M};}}"
            f"QComboBox#{name}::drop-down{{border:none;width:18px;}}"
            f"QComboBox#{name}::down-arrow{{width:0;height:0;"
            f"border-left:4px solid transparent;border-right:4px solid transparent;"
            f"border-top:5px solid {self._TEXT_S};}}"
            f"QComboBox#{name} QAbstractItemView{{background:{self._SURF3};color:{self._TEXT};"
            f"border-radius:6px;selection-background-color:{self._SURF4};border:1px solid {self._BORDER_M};"
            f"outline:none;padding:4px;}}"
        )
 
    def _s_spin(self, name):
        return (
            f"QSpinBox#{name}{{background:{self._SURF2};border:1px solid {self._BORDER};"
            f"border-radius:6px;color:{self._TEXT};padding:0 8px;}}"
            f"QSpinBox#{name}:focus{{border-color:{self._BORDER_M};}}"
            f"QSpinBox#{name}::up-button,QSpinBox#{name}::down-button{{width:0;}}"
        )
 
    def _s_list(self):
        return (
            f"QListWidget#LBEntryList{{background:transparent;border:none;outline:none;padding:2px;}}"
            f"QListWidget#LBEntryList::item{{background:{self._SURF2};border:1px solid transparent;"
            f"border-radius:8px;padding:9px 12px;color:{self._TEXT_S};margin-bottom:4px;}}"
            f"QListWidget#LBEntryList::item:hover{{background:{self._SURF3};color:{self._TEXT};"
            f"border-color:{self._BORDER};}}"
            f"QListWidget#LBEntryList::item:selected{{background:{self._ACC_MUT};"
            f"border:1px solid {self._ACC_GLO};color:{self._TEXT};}}"
        )
 
    def _s_action_btn(self, name):
        return (
            f"QPushButton#{name}{{background:{self._SURF2};border:1px solid {self._BORDER_M};"
            f"border-radius:6px;color:{self._TEXT};}}"
            f"QPushButton#{name}:hover{{background:{self._SURF3};"
            f"border-color:rgba(255,255,255,0.16);}}"
        )

    def _s_accent_btn(self, name):
        return (
            f"QPushButton#{name}{{background:{self._ACC_MUT};border:1px solid {self._ACC_GLO};"
            f"border-radius:6px;color:{self._ACCENT};letter-spacing:0.5px;}}"
            f"QPushButton#{name}:hover{{background:rgba(196,154,56,0.27);"
            f"border-color:rgba(196,154,56,0.52);color:{self._ACC_BRT};}}"
        )

    def _s_danger_btn(self, name):
        return (
            f"QPushButton#{name}{{background:{self._DNG_MUT};border:1px solid rgba(196,64,64,0.2);"
            f"border-radius:6px;color:{self._DANGER};}}"
            f"QPushButton#{name}:hover{{background:{self._DNG_GLO};"
            f"border-color:rgba(196,64,64,0.45);color:#EE7777;}}"
        )

    def load_lorebooks(self):
        self.lorebooks = (
            self.configuration_settings
            .load_configuration()
            .get("user_data", {})
            .get("lorebooks", {})
        )
 
    def update_lorebook_combo(self):
        self.lorebook_combo.blockSignals(True)
        self.lorebook_combo.clear()
        for name in sorted(self.lorebooks.keys()):
            self.lorebook_combo.addItem(name)
        self.lorebook_combo.blockSignals(False)
 
    def apply_current_lorebook(self):
        name = self.lorebook_combo.currentText()
        if name in self.lorebooks:
            self.current_lorebook_name = name
            self.current_entry_index   = -1
            self.depth_combo.setCurrentIndex(
                max(0, self.lorebooks[name].get("n_depth", 3) - 1)
            )
            self.form_widget.setVisible(False)
            self.empty_state.setVisible(True)
            self.populate_entry_list()

        self._update_token_count()
 
    def populate_entry_list(self):
        self.entry_list.clear()
        if not self.current_lorebook_name:
            self.lbl_count.setText("0 " + self.translations.get("lorebook_editor_suffix_entries", "entries")); return
 
        entries = self.lorebooks[self.current_lorebook_name].get("entries", [])
        filt    = self.search_bar.text().lower()
        shown   = 0
 
        for i, e in enumerate(entries):
            abbr    = _TRIGGER_ABBR.get(e.get("trigger_type", "keyword"), "KW")
            name    = e.get("name", "Unnamed")
            display = f"[{abbr}]  {name}"
            if filt and filt not in name.lower() and filt not in abbr.lower():
                continue
            it = QListWidgetItem(display)
            it.setData(Qt.ItemDataRole.UserRole, i)
            it.setSizeHint(QtCore.QSize(0, 40))
            self.entry_list.addItem(it)
            shown += 1
 
        total = len(entries)
        if filt:
            self.lbl_count.setText(
                self.translations.get("lorebook_entries_shown", "{shown} of {total} entries").format(shown=shown, total=total)
            )
        else:
            self.lbl_count.setText(
                self.translations.get("lorebook_entries_count", "{total} entries").format(total=total)
            )
 
    def select_entry(self, item):
        if not item or self.current_lorebook_name not in self.lorebooks:
            return
        self.current_entry_index = item.data(Qt.ItemDataRole.UserRole)
        entries = self.lorebooks[self.current_lorebook_name]["entries"]
        if self.current_entry_index >= len(entries):
            return
        e = entries[self.current_entry_index]
 
        self.is_programmatic_change = True
 
        self.input_name.setText(e.get("name", "Unnamed"))
        self.input_content.setPlainText(e.get("content", ""))
        self.combo_inj.setCurrentIndex(1 if e.get("injection_behavior") == "active" else 0)
 
        t   = e.get("trigger_type", "keyword")
        idx = _TRIGGER_KEYS.index(t) if t in _TRIGGER_KEYS else 0
        self.combo_type.setCurrentIndex(idx)
        self.stack_triggers.setCurrentIndex(idx)
        self.lbl_trig_title.setText(self._trig_card_titles.get(idx, self.translations.get("lorebook_trigger_config_label", "TRIGGER CONFIGURATION")))
 
        self.input_keys.setText(", ".join(e.get("key", [])))
        self.input_exclude.setText(", ".join(e.get("exclude_key", [])))
        self.input_semantic.setPlainText(e.get("semantic_trigger", ""))

        def safe_int(val, default=0):
            try:
                return int(val)
            except (ValueError, TypeError):
                return default

        self.spin_chain.setValue(safe_int(e.get("depends_on", -1), -1))
        self.spin_chain_del.setValue(safe_int(e.get("chain_delay", 0), 0))
        self.spin_min.setValue(safe_int(e.get("min_msg", 0), 0))
        self.spin_max.setValue(safe_int(e.get("max_msg", 9999), 9999))
        self.spin_sticky.setValue(safe_int(e.get("sticky", 0), 0))
        self.spin_cd.setValue(safe_int(e.get("cooldown", 0), 0))
        self.spin_delay.setValue(safe_int(e.get("delay", 0), 0))
        self.spin_prob.setValue(safe_int(e.get("probability", 100), 100))
 
        self.is_programmatic_change = False
        self.empty_state.setVisible(False)
        self.form_widget.setVisible(True)

        self._update_token_count()
 
    def save_current_entry_changes(self):
        if self.is_programmatic_change or self.current_entry_index < 0:
            return
        lb = self.lorebooks.get(self.current_lorebook_name)
        if not lb:
            return
        entries = lb["entries"]
        if self.current_entry_index >= len(entries):
            return
 
        e = entries[self.current_entry_index]
        e["name"]               = self.input_name.text().strip() or "Unnamed"
        e["content"]            = self.input_content.toPlainText()
        e["injection_behavior"] = "active" if self.combo_inj.currentIndex() == 1 else "passive"
 
        idx = self.combo_type.currentIndex()
        e["trigger_type"] = _TRIGGER_KEYS[idx]
 
        if idx == 0:
            e["key"]         = [k.strip() for k in self.input_keys.text().split(",") if k.strip()]
            e["exclude_key"] = [k.strip() for k in self.input_exclude.text().split(",") if k.strip()]
        elif idx == 1:
            e["semantic_trigger"] = self.input_semantic.toPlainText()
        elif idx == 4:
            e["depends_on"]  = self.spin_chain.value()
            e["chain_delay"] = self.spin_chain_del.value()
        elif idx == 5:
            e["min_msg"] = self.spin_min.value()
            e["max_msg"] = self.spin_max.value()
 
        e["sticky"]      = self.spin_sticky.value()
        e["cooldown"]    = self.spin_cd.value()
        e["delay"]       = self.spin_delay.value()
        e["probability"] = self.spin_prob.value()
 
        self.configuration_settings.update_lorebook(self.current_lorebook_name, lb)
 
        it = self.entry_list.currentItem()
        if it:
            abbr = _TRIGGER_ABBR.get(_TRIGGER_KEYS[idx], "KW")
            it.setText(f"[{abbr}]  {e['name']}")

        self._update_token_count()
 
    def on_type_changed(self, idx):
        self.stack_triggers.setCurrentIndex(idx)
        self.lbl_trig_title.setText(self._trig_card_titles.get(idx, self.translations.get("lorebook_trigger_config_label", "TRIGGER CONFIGURATION")))
        self.save_current_entry_changes()

    def add_entry(self):
        if not self.current_lorebook_name:
            return
        entries = self.lorebooks[self.current_lorebook_name]["entries"]
        uid = max((e.get("uid", i) for i, e in enumerate(entries)), default=-1) + 1
        entries.append({
            "name": "New Entry", "uid": uid,
            "key": [], "exclude_key": [], "content": "",
            "trigger_type": "keyword", "probability": 100,
            "sticky": 0, "cooldown": 0, "delay": 0,
            "injection_behavior": "passive",
        })
        self.populate_entry_list()
        self.entry_list.setCurrentRow(self.entry_list.count() - 1)
        self.select_entry(self.entry_list.currentItem())
        self.input_name.setFocus(); self.input_name.selectAll()
 
    def delete_entry(self):
        if self.current_entry_index < 0:
            return
        
        title = self.translations.get("lorebook_editor_delete", "Delete Entry")
        text = self.translations.get("lorebook_delete_entry_confirm", "Delete this entry? This cannot be undone.")

        if (SowConfirmDialog(self, title, text, danger=True).exec() == QDialog.DialogCode.Accepted):
            self.lorebooks[self.current_lorebook_name]["entries"].pop(self.current_entry_index)
            self.current_entry_index = -1
            self.form_widget.setVisible(False)
            self.empty_state.setVisible(True)
            self.populate_entry_list()

        self._update_token_count()

    def _show_name_dialog(self, title: str, label_text: str, default_text: str = "") -> str | None:
        dialog = SowInputDialog(
            parent=self,
            title=title,
            label=label_text,
            text=default_text,
            placeholder=default_text or "Enter name..."
        )
        
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            return dialog.get_text()
        return None
    
    def create_lorebook(self):
        title = self.translations.get("lorebook_editor_new_lorebook", "New Lorebook")
        label = self.translations.get("lorebook_editor_lorebook_name", "Name:")

        name = self._show_name_dialog(title, label)
        
        if not name:
            return

        if name in self.lorebooks:
            error_title = self.translations.get("lorebook_editor_rename_error_title", "Error")
            error_text = self.translations.get("lorebook_editor_rename_error_exists", "A lorebook with this name already exists.")
            sow_toast(self.main_window, error_title, error_text, "error")
            return
        
        self.lorebooks[name] = {"name": name, "n_depth": 3, "entries": []}
        self.configuration_settings.update_lorebook(name, self.lorebooks[name])
        self.load_lorebooks()
        self.update_lorebook_combo()
        self.lorebook_combo.setCurrentText(name)
        self.apply_current_lorebook()
 
    def rename_lorebook_action(self):
        old = self.lorebook_combo.currentText()
        if not old: return

        title = self.translations.get("lorebook_editor_rename_lorebook", "Rename Lorebook")
        label = self.translations.get("lorebook_editor_rename_label", "New name for '{name}':").format(name=old)

        new = self._show_name_dialog(title, label, default_text=old)
        
        if not new or new == old:
            return

        data = self.lorebooks.pop(old)
        data["name"] = new
        self.lorebooks[new] = data
        
        self.configuration_settings.delete_lorebook(old)
        self.configuration_settings.update_lorebook(new, data)
        self.current_lorebook_name = new
        self.load_lorebooks()
        self.update_lorebook_combo()
        self.lorebook_combo.setCurrentText(new)
 
    def delete_lorebook_action(self):
        name = self.lorebook_combo.currentText()
        if not name: return

        title = self.translations.get("lorebook_editor_delete_lorebook", "Delete Lorebook")
        text = self.translations.get("lorebook_delete_lb_confirm", 'Delete "{name}" and all its entries?').format(name=name)

        if (SowConfirmDialog(self, title, text, danger=True).exec() == QDialog.DialogCode.Accepted):
            del self.lorebooks[name]
            self.configuration_settings.delete_lorebook(name)
            self.current_lorebook_name = None; self.current_entry_index = -1
            self.load_lorebooks(); self.update_lorebook_combo()
            if self.lorebook_combo.count() > 0:
                self.apply_current_lorebook()
            else:
                self.entry_list.clear(); self.lbl_count.setText("0 " + self.translations.get("lorebook_editor_suffix_entries", "entries"))
                self.form_widget.setVisible(False); self.empty_state.setVisible(True)

    def global_save(self):
        if self.current_lorebook_name:
            self.lorebooks[self.current_lorebook_name]["n_depth"] = (
                self.depth_combo.currentIndex() + 1
            )
        self.configuration_settings.save_lorebooks(self.lorebooks)
        
        title = self.translations.get("lorebook_editor_saved", "Saved")
        text = self.translations.get("lorebook_editor_saved_desc", "Lorebooks saved successfully.")
        sow_toast(self.main_window, title, text, "success")
 
    def export_lorebook_action(self):
        name = self.lorebook_combo.currentText()
        if not name: return

        title = self.translations.get("lorebook_editor_export_lorebook", "Export Lorebook")
        path, _ = QFileDialog.getSaveFileName(self, title, f"{name}.json", "JSON (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.lorebooks[name], f, ensure_ascii=False, indent=4)
            
            toast_title = self.translations.get("lorebook_editor_export_success", "Export Success")
            toast_text = self.translations.get("lorebook_export_success_toast", '"{name}" saved to disk.').format(name=name)
            sow_toast(self.main_window, toast_title, toast_text, "success")
 
    def import_lorebook_action(self):
        title = self.translations.get("lorebook_editor_import_lorebook", "Import Lorebook")
        path, _ = QFileDialog.getOpenFileName(self, title, "", "JSON (*.json)")
        if not path: return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            raw_entries = data.get("entries", [])
            if isinstance(raw_entries, dict):
                data["entries"] = list(raw_entries.values())
            elif not isinstance(raw_entries, list):
                data["entries"] = []

            name = data.get("name", "Imported")
            while name in self.lorebooks:
                name += "_copy"
            self.lorebooks[name] = data
            self.configuration_settings.update_lorebook(name, data)
            self.load_lorebooks(); self.update_lorebook_combo()
            self.lorebook_combo.setCurrentText(name); self.apply_current_lorebook()
        except Exception as exc:
            error_title = self.translations.get("lorebook_editor_import_error", "Import Error")
            sow_toast(self.main_window, error_title, str(exc), "error")

    def _count_tokens(self, text: str) -> int:
        if not text:
            return 0
        try:
            return len(self.tokenizer.encode(text))
        except Exception:
            return len(text) // 4

    def _update_token_count(self):
        if not hasattr(self, 'token_counter_lbl'):
            return

        if not self.current_lorebook_name or self.current_lorebook_name not in self.lorebooks:
            self.token_counter_lbl.setText("Tokens: 0")
            self.token_counter_lbl.setStyleSheet(f"color: {self._TEXT_S}; margin-left: 12px; background: transparent; border: none;")
            return

        entry_texts = [
            self.input_name.text().strip(),
            self.input_content.toPlainText().strip(),
            self.input_keys.text().strip(),
            self.input_exclude.text().strip(),
            self.input_semantic.toPlainText().strip()
        ]
        entry_tokens = sum(self._count_tokens(t) for t in entry_texts)

        lb = self.lorebooks[self.current_lorebook_name]
        total_tokens = 0
        for e in lb.get("entries", []):
            total_tokens += self._count_tokens(e.get("name", ""))
            total_tokens += self._count_tokens(e.get("content", ""))
            total_tokens += self._count_tokens(" ".join(e.get("key", [])))
            total_tokens += self._count_tokens(" ".join(e.get("exclude_key", [])))
            total_tokens += self._count_tokens(e.get("semantic_trigger", ""))

        if entry_tokens < 300:
            color = "#4ADE80"  # Optimal
            weight = "Optimal"
        elif entry_tokens < 800:
            color = "#E2B34C"  # Heavy
            weight = "Heavy"
        else:
            color = "#C44040"  # Warning
            weight = "Critical"

        if self.current_entry_index >= 0:
            self.token_counter_lbl.setText(f"Entry: <b style='color:{color};'>{entry_tokens}</b> ({weight}) · Book Total: <b>{total_tokens}</b>")
        else:
            self.token_counter_lbl.setText(f"Book Total: <b>{total_tokens}</b> tokens")

        self.token_counter_lbl.setStyleSheet(f"color: {self._TEXT}; margin-left: 12px; background: transparent; border: none; font-size: 11px;")

class AuthorNotesEditorDialog(QDialog):
    _BG       = "#0C0C10"
    _SURF1    = "#111117"
    _SURF2    = "#18181F"
    _SURF3    = "#1F1F27"
    _TEXT     = "#DEDAD2"
    _TEXT_S   = "#6F6B63"
    _BORDER   = "rgba(255,255,255,0.055)"
    _BORDER_M = "rgba(255,255,255,0.10)"
    
    _BLUE_ACCENT = "#4BB8FF"
    _BLUE_MUT    = "rgba(75, 184, 255, 0.15)"
    _BLUE_GLO    = "rgba(75, 184, 255, 0.35)"
    _BLUE_HOV_BG = "rgba(75, 184, 255, 0.25)"
    _BLUE_HOV_BD = "rgba(75, 184, 255, 0.55)"
    _BLUE_BRT    = "#82CDFF"

    def __init__(self, translations, configuration_settings, main_window, parent=None):
        super().__init__(parent)
        self.translations = translations
        self.configuration_settings = configuration_settings
        self.main_window = main_window

        self.setWindowTitle(self.translations.get("author_notes_editor_title", "Author Notes Editor"))
        self.setWindowIcon(QIcon("app/gui/icons/logotype.ico"))
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setMinimumSize(740, 520)
        self.resize(760, 560)

        self._init_fonts()
        self._apply_base_palette()
        self.setup_ui()
        self.load_data()

    def _init_fonts(self):
        def mf(size, weight=QFont.Weight.Normal):
            f = QFont("Inter Tight", size, weight)
            f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            return f

        self.f_title = mf(13, QFont.Weight.Bold)
        self.f_label = mf(8,  QFont.Weight.Bold)
        self.f_input = mf(10)
        self.f_btn   = mf(10, QFont.Weight.DemiBold)
        self.f_desc  = mf(10, QFont.Weight.Medium)

    def _apply_base_palette(self):
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor(self._BG))
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_toolbar())
        root.addWidget(self._build_body(), 1)
        root.addWidget(self._build_footer())

    def _build_toolbar(self):
        bar = QFrame()
        bar.setObjectName("ANToolbar")
        bar.setFixedHeight(56)
        bar.setStyleSheet(
            "QFrame#ANToolbar {"
            f"  background: {self._SURF1};"
            f"  border-bottom: 1px solid {self._BORDER};"
            "}"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(12)

        title_lbl = QLabel(self.translations.get("author_notes_header_title", "AUTHOR NOTES ENGINE"))
        title_lbl.setFont(self.f_title)
        title_lbl.setStyleSheet(f"color: {self._TEXT};")

        sep = QFrame()
        sep.setFixedSize(1, 24)
        sep.setStyleSheet(f"background: {self._BORDER};")

        sub_lbl = QLabel(self.translations.get("author_notes_subtitle", "GLOBAL NARRATIVE DIRECTIVES"))
        sub_lbl.setFont(self.f_label)
        sub_lbl.setStyleSheet(f"color: {self._TEXT_S}; letter-spacing: 1.1px;")

        lay.addWidget(title_lbl)
        lay.addWidget(sep)
        lay.addWidget(sub_lbl)
        lay.addStretch()

        return bar

    def _build_body(self):
        body = QFrame()
        body.setStyleSheet(f"background: {self._BG}; border: none;")
        lay = QVBoxLayout(body)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(16)

        desc_lbl = QLabel(self.translations.get(
            "author_notes_hint", 
            "These instructions are injected dynamically into the context window. Use them to guide the character's behavior, enforce a specific writing style, or set overarching scenario goals."
        ))
        desc_lbl.setFont(self.f_desc)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(f"color: {self._TEXT_S}; line-height: 1.4;")
        lay.addWidget(desc_lbl)

        input_lbl = QLabel(self.translations.get("author_notes_input_label", "DIRECTIVES CONTENT"))
        input_lbl.setFont(self.f_label)
        input_lbl.setStyleSheet(f"color: {self._TEXT_S}; letter-spacing: 0.8px;")
        lay.addWidget(input_lbl)

        self.notes_edit = QTextEdit()
        self.notes_edit.setObjectName("ANInputContent")
        self.notes_edit.setFont(self.f_input)
        self.notes_edit.setAcceptRichText(False)
        self.notes_edit.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        self.notes_edit.setPlaceholderText(
            self.translations.get("author_notes_editor_placeholder", "Enter your instructions or hints for the character here...")
        )
        self.notes_edit.setStyleSheet(
            f"QTextEdit#ANInputContent {{"
            f"  background: {self._SURF2};"
            f"  border: 1px solid {self._BORDER};"
            f"  border-radius: 8px;"
            f"  color: {self._TEXT};"
            f"  padding: 12px 14px;"
            f"  selection-background-color: {self._BLUE_MUT};"
            f"}}"
            f"QTextEdit#ANInputContent:focus {{"
            f"  border-color: {self._BORDER_M};"
            f"  background: {self._SURF3};"
            f"}}"
        )
        lay.addWidget(self.notes_edit, 1)

        return body

    def _build_footer(self):
        bar = QFrame()
        bar.setObjectName("ANFooter")
        bar.setFixedHeight(64)
        bar.setStyleSheet(
            "QFrame#ANFooter {"
            f"  background: {self._SURF1};"
            f"  border-top: 1px solid {self._BORDER};"
            "}"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 24, 0)
        lay.setSpacing(12)

        lay.addStretch()

        btn_cancel = QPushButton(self.translations.get("author_notes_editor_cancel", "CANCEL"))
        btn_cancel.setObjectName("ANBtnCancel")
        btn_cancel.setFixedSize(110, 36)
        btn_cancel.setFont(self.f_btn)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(
            f"QPushButton#ANBtnCancel {{"
            f"  background: transparent;"
            f"  border: 1px solid {self._BORDER};"
            f"  border-radius: 6px;"
            f"  color: {self._TEXT_S};"
            f"  letter-spacing: 0.5px;"
            f"}}"
            f"QPushButton#ANBtnCancel:hover {{"
            f"  background: {self._SURF2};"
            f"  border-color: {self._BORDER_M};"
            f"  color: {self._TEXT};"
            f"}}"
        )
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton(self.translations.get("author_notes_editor_save", "SAVE DIRECTIVES"))
        btn_save.setObjectName("ANBtnSave")
        btn_save.setFixedSize(160, 36)
        btn_save.setFont(self.f_btn)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(
            f"QPushButton#ANBtnSave {{"
            f"  background: {self._BLUE_MUT};"
            f"  border: 1px solid {self._BLUE_GLO};"
            f"  border-radius: 6px;"
            f"  color: {self._BLUE_ACCENT};"
            f"  letter-spacing: 0.5px;"
            f"}}"
            f"QPushButton#ANBtnSave:hover {{"
            f"  background: {self._BLUE_HOV_BG};"
            f"  border-color: {self._BLUE_HOV_BD};"
            f"  color: {self._BLUE_BRT};"
            f"}}"
        )
        btn_save.clicked.connect(self.save_notes)

        lay.addWidget(btn_cancel)
        lay.addWidget(btn_save)

        return bar

    def load_data(self):
        current_notes = self.configuration_settings.get_user_data("author_notes") or ""
        self.notes_edit.setPlainText(current_notes)

    def save_notes(self):
        new_notes = self.notes_edit.toPlainText().strip()
        self.configuration_settings.update_user_data("author_notes", new_notes)

        sow_toast(
            parent=self.main_window,
            title=self.translations.get("author_notes_title", "Author's Notes"),
            text=self.translations.get("author_notes_saved_body", "The author's notes were saved successfully."),
            msg_type="success"
        )
        self.accept()

class SummaryEditorDialog(QDialog):
    _BG       = "#0C0C10"
    _SURF1    = "#111117"
    _SURF2    = "#18181F"
    _SURF3    = "#1F1F27"
    _TEXT     = "#DEDAD2"
    _TEXT_S   = "#6F6B63"
    _BORDER   = "rgba(255,255,255,0.055)"
    _BORDER_M = "rgba(255,255,255,0.10)"
    
    _ACCENT   = "#C49A38"
    _ACC_MUT  = "rgba(196,154,56,0.15)"
    _ACC_GLO  = "rgba(196,154,56,0.32)"
    _ACC_BRT  = "#E2B34C"

    _BLUE     = "#4BB8FF"
    _BLUE_MUT = "rgba(75, 184, 255, 0.15)"
    _BLUE_GLO = "rgba(75, 184, 255, 0.35)"
    _BLUE_BRT = "#82CDFF"

    _DANGER   = "#C44040"
    _DNG_MUT  = "rgba(196,64,64,0.13)"
    _DNG_GLO  = "rgba(196,64,64,0.28)"

    def __init__(self, translations, configuration_characters, configuration_settings, character_name, conversation_method, main_window, parent=None):
        super().__init__(parent)
        self.translations = translations
        self.configuration_characters = configuration_characters
        self.configuration_settings = configuration_settings
        self.prompt_engine = PromptEngine()
        self.main_window = main_window
        self.character_name = character_name
        self.conversation_method = conversation_method

        self.char_config = self.configuration_characters.load_configuration()
        
        if not character_name or character_name not in self.char_config["character_list"]:
            return

        char_data = self.char_config["character_list"][character_name]
        current_chat_id = char_data.get("current_chat", "default")
        self.chat_data = char_data["chats"].get(current_chat_id, {})

        self.current_summary_text = self.chat_data.get("summary_text", "")
        self.last_seq = self.chat_data.get("last_summarized_sequence", 0)

        self.current_prompt = self.configuration_settings.get_main_setting("prompt_summary")
        if not self.current_prompt:
            self.current_prompt = ("""
                You are an expert narrative archivist. Your task is to update the ongoing story summary by seamlessly merging the previous summary with the new recent messages. 

                CRITICAL RULES:
                1. DO NOT write the story any further or generate new dialogue. Summarize ONLY what has already happened.
                2. DO NOT drop overarching plot points, long-term goals, or previously established vital facts. Retain the core history while adding new developments.
                3. STRICT LENGTH LIMIT: Keep the entire output under 500 words. 
                4. COMPRESSION: Aggressively condense older events into single, short sentences. Only expand on the events that happened in the most recent messages.
                5. NO REPETITION: Do not repeat facts, phrases, or sentences. Once a detail (like clothing or an action) is mentioned in one section, do not repeat it in another.
                6. You MUST strictly follow this exact format and use these exact tags:

                [CHARACTER STATES & INVENTORY]
                Detailed physical and mental state of all present characters. List active injuries, current clothing/armor, and exact inventory/items. Include their immediate short-term motives and long-term overarching goals. Do not use past tense.

                [RELATIONSHIP DYNAMICS]
                How the relationship between the characters is currently evolving. Explicitly mention current trust levels, power balance (who is leading/following), unspoken tensions, promises made to each other, and hidden secrets they are keeping from one another.

                [CURRENT SCENE & ATMOSPHERE]
                Exact current location and spatial positioning of the characters. Include rich sensory details (weather, lighting, time of day, atmosphere, smells). Clearly state any immediate dangers, time limits, or unresolved hooks in the room/area.

                [KEY DISCOVERIES & LORE]
                Any new vital information learned about the world, NPCs, magic, technology, or the main plot. If a character revealed a backstory or a secret, document it here. If nothing new was discovered recently, keep the established lore from the previous summary.

                [CHRONOLOGICAL EVENTS]
                A dense, chronological bullet-point list of the most critical actions and plot beats. 
                - Discard only purely filler dialogue (e.g., greetings). 
                - MUST retain the essence of dialogues that reveal character motives, plot progression, or major decisions. 
                - Focus heavily on cause and effect (e.g., "Character A did X, which caused Character B to feel Y").
            """)

        self.setWindowTitle(self.translations.get("summary_editor_title", "Story Memory Editor"))
        self.setWindowIcon(QIcon("app/gui/icons/logotype.ico"))
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowMinMaxButtonsHint
        )
        self.setMinimumSize(840, 720)

        self._init_fonts()
        self._apply_base_palette()
        self.setup_ui()
        self.setup_logic()

    def _init_fonts(self):
        def mf(size, weight=QFont.Weight.Normal):
            f = QFont("Inter Tight", size, weight)
            f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            return f

        self.f_title = mf(13, QFont.Weight.Bold)
        self.f_label = mf(8,  QFont.Weight.Bold)
        self.f_input = mf(10)
        self.f_badge = mf(9,  QFont.Weight.DemiBold)
        self.f_btn   = mf(10, QFont.Weight.DemiBold)

    def _apply_base_palette(self):
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor(self._BG))
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_toolbar())
        root.addWidget(self._build_body(), 1)
        root.addWidget(self._build_footer())

    def _build_toolbar(self):
        bar = QFrame()
        bar.setObjectName("SumToolbar")
        bar.setFixedHeight(56)
        bar.setStyleSheet(
            "QFrame#SumToolbar {"
            f"  background: {self._SURF1};"
            f"  border-bottom: 1px solid {self._BORDER};"
            "}"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(12)

        title_lbl = QLabel(self.translations.get("summary_editor_header_title", "SOUL MEMORY"))
        title_lbl.setFont(self.f_title)
        title_lbl.setStyleSheet(f"color: {self._TEXT};")

        sep = QFrame()
        sep.setFixedSize(1, 24)
        sep.setStyleSheet(f"background: {self._BORDER};")

        sub_lbl = QLabel(self.translations.get("summary_editor_subtitle", "ARCHIVE & COMPRESSION"))
        sub_lbl.setFont(self.f_label)
        sub_lbl.setStyleSheet(f"color: {self._TEXT_S}; letter-spacing: 1.1px;")

        lay.addWidget(title_lbl)
        lay.addWidget(sep)
        lay.addWidget(sub_lbl)
        lay.addStretch()

        self.status_label = QLabel(self._get_status_text())
        self.status_label.setFont(self.f_badge)
        self.status_label.setStyleSheet(
            f"color: {self._BLUE};"
        )
        lay.addWidget(self.status_label)

        return bar

    def _build_body(self):
        body = QFrame()
        body.setStyleSheet(f"background: {self._BG}; border: none;")
        lay = QVBoxLayout(body)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(16)

        lbl_memory = QLabel(self.translations.get("summary_editor_current_memory_label", "CURRENT MEMORY ARCHIVE"))
        lbl_memory.setFont(self.f_label)
        lbl_memory.setStyleSheet(f"color: {self._TEXT_S}; letter-spacing: 0.8px;")
        lay.addWidget(lbl_memory)

        self.summary_edit = QTextEdit()
        self.summary_edit.setObjectName("SumArchive")
        self.summary_edit.setFont(self.f_input)
        self.summary_edit.setAcceptRichText(False)
        self.summary_edit.setPlaceholderText(self.translations.get("summary_editor_memory_empty", "The memory archive is currently empty..."))
        self.summary_edit.setPlainText(self.current_summary_text)
        self.summary_edit.setStyleSheet(self._s_textedit("SumArchive"))
        lay.addWidget(self.summary_edit, stretch=1)

        lay.addSpacing(8)

        lbl_prompt = QLabel(self.translations.get("summary_editor_prompt_label", "SUMMARIZATION DIRECTIVES (PROMPT)"))
        lbl_prompt.setFont(self.f_label)
        lbl_prompt.setStyleSheet(f"color: {self._TEXT_S}; letter-spacing: 0.8px;")
        lay.addWidget(lbl_prompt)

        self.prompt_edit = QTextEdit()
        self.prompt_edit.setObjectName("SumPrompt")
        self.prompt_edit.setFont(self.f_input)
        self.prompt_edit.setAcceptRichText(False)
        self.prompt_edit.setPlaceholderText(self.translations.get("summary_editor_instruction_placeholder", "Enter instructions for the AI..."))
        self.prompt_edit.setPlainText(self.current_prompt)
        self.prompt_edit.setStyleSheet(self._s_textedit("SumPrompt"))
        
        self.prompt_edit.setFixedHeight(120)
        self.prompt_edit.textChanged.connect(self._adjust_prompt_height)
        lay.addWidget(self.prompt_edit, stretch=0)

        QTimer.singleShot(50, self._adjust_prompt_height)

        return body

    def _build_footer(self):
        bar = QFrame()
        bar.setObjectName("SumFooter")
        bar.setFixedHeight(64)
        bar.setStyleSheet(
            "QFrame#SumFooter {"
            f"  background: {self._SURF1};"
            f"  border-top: 1px solid {self._BORDER};"
            "}"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 24, 0)
        lay.setSpacing(12)

        self.clear_btn = QPushButton(self.translations.get("summary_editor_clear", "CLEAR MEMORY"))
        self.clear_btn.setObjectName("SumBtnClear")
        self.clear_btn.setFixedSize(140, 36)
        self.clear_btn.setFont(self.f_btn)
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.setStyleSheet(
            f"QPushButton#SumBtnClear {{ background: transparent; border: 1px solid {self._DNG_GLO}; border-radius: 6px; color: {self._DANGER}; letter-spacing: 0.5px; }}"
            f"QPushButton#SumBtnClear:hover {{ background: {self._DNG_MUT}; border-color: rgba(196,64,64,0.45); color: #EE7777; }}"
        )

        lay.addWidget(self.clear_btn)
        lay.addStretch()

        self.generate_btn = QPushButton(self.translations.get("summary_editor_generate", "GENERATE SUMMARY"))
        self.generate_btn.setObjectName("SumBtnGen")
        self.generate_btn.setFixedSize(180, 36)
        self.generate_btn.setFont(self.f_btn)
        self.generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.generate_btn.setToolTip(self.translations.get("summary_editor_tooltip", "Uses the directives to summarize recent messages immediately."))
        self.generate_btn.setStyleSheet(
            f"QToolTip {{ background-color: {self._SURF3}; color: {self._TEXT}; border: 1px solid {self._BORDER_M}; border-radius: 6px; padding: 6px; }}"
            f"QPushButton#SumBtnGen {{ background: {self._BLUE_MUT}; border: 1px solid {self._BLUE_GLO}; border-radius: 6px; color: {self._BLUE}; }}"
            f"QPushButton#SumBtnGen:hover {{ background: rgba(75, 184, 255, 0.25); border-color: rgba(75, 184, 255, 0.55); color: {self._BLUE_BRT}; }}"
        )

        self.save_btn = QPushButton(self.translations.get("summary_editor_save", "SAVE CHANGES"))
        self.save_btn.setObjectName("SumBtnSave")
        self.save_btn.setFixedSize(160, 36)
        self.save_btn.setFont(self.f_btn)
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setStyleSheet(
            f"QPushButton#SumBtnSave {{ background: {self._BLUE_MUT}; border: 1px solid {self._BLUE_GLO}; border-radius: 6px; color: {self._BLUE}; }}"
            f"QPushButton#SumBtnSave:hover {{ background: rgba(75, 184, 255, 0.25); border-color: rgba(75, 184, 255, 0.55); color: {self._BLUE_BRT}; }}"
        )

        lay.addWidget(self.generate_btn)
        lay.addWidget(self.save_btn)

        return bar

    def _s_textedit(self, name):
        return (
            f"QTextEdit#{name} {{"
            f"  background: {self._SURF2};"
            f"  border: 1px solid {self._BORDER};"
            f"  border-radius: 8px;"
            f"  color: {self._TEXT};"
            f"  padding: 12px 14px;"
            f"  selection-background-color: {self._BLUE_MUT};"
            f"  line-height: 1.4;"
            f"}}"
            f"QTextEdit#{name}:focus {{"
            f"  border-color: {self._BORDER_M};"
            f"  background: {self._SURF3};"
            f"}}"
        )

    def _get_status_text(self):
        return self.translations.get("summary_editor_covered_badge", "History: 1-{last_seq}").format(last_seq=self.last_seq)

    def _adjust_prompt_height(self):
        doc_height = self.prompt_edit.document().size().height()
        margins = self.prompt_edit.contentsMargins()
        target_height = int(doc_height) + margins.top() + margins.bottom() + 26
        
        new_height = max(100, min(target_height, 350))
        self.prompt_edit.setFixedHeight(new_height)

    def setup_logic(self):
        self.save_btn.clicked.connect(self.save_all)
        self.clear_btn.clicked.connect(self.clear_summary)
        self.generate_btn.clicked.connect(self.force_update)

    def save_all(self):
        new_text = self.summary_edit.toPlainText().strip()
        self.chat_data["summary_text"] = new_text
        self.configuration_characters.save_configuration_edit(self.char_config)

        new_prompt_text = self.prompt_edit.toPlainText().strip()
        self.configuration_settings.update_main_setting("prompt_summary", new_prompt_text)

        sow_toast(
            parent=self.main_window,
            title=self.translations.get("summary_editor_header_title", "Story Memory"),
            text=self.translations.get("summary_editor_saved_toast", "Memory and directives saved successfully."),
            msg_type="success"
        )

    def clear_summary(self):
        title = self.translations.get("summary_editor_clear_title", "Clear Memory?")
        message = self.translations.get("summary_editor_clear_text", "Are you sure you want to delete the story memory?")

        dialog = SowConfirmDialog(
            parent=self.main_window,
            title=title,
            text=message,
            confirm_text="Clear",
            danger=True
        )

        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.summary_edit.clear()
            self.last_seq = 0
            self.status_label.setText(self._get_status_text())

            self.chat_data["last_summarized_sequence"] = self.last_seq
            self.configuration_characters.save_configuration_edit(self.char_config)

    def force_update(self):
        new_prompt_text = self.prompt_edit.toPlainText().strip()
        self.configuration_settings.update_main_setting("prompt_summary", new_prompt_text)
        
        interval = int(self.configuration_settings.get_main_setting("interval_summary") or 20)
        
        raw_messages = self.chat_data.get("chat_content", {}).values()
        sorted_messages = sorted(raw_messages, key=lambda x: x.get("sequence_number", 0))
        
        new_messages_chunk = []
        highest_seq_in_chunk = self.last_seq
        
        for msg in sorted_messages:
            seq = msg.get("sequence_number", 0)
            
            if seq > self.last_seq:
                current_var_id = msg.get("current_variant_id", "default")
                text_content = ""
                
                for variant in msg.get("variants", []):
                    if variant.get("variant_id") == current_var_id:
                        text_content = variant.get("text", "")
                        break
                
                if not text_content.strip():
                    continue
                
                role = "user" if msg.get("is_user") else "assistant"
                new_messages_chunk.append({"role": role, "content": text_content})
                highest_seq_in_chunk = seq
                
                if len(new_messages_chunk) >= interval:
                    break
        
        if not new_messages_chunk:
            sow_toast(
                parent=self,
                title=self.translations.get("info_title", "Info"),
                text=self.translations.get("summary_editor_no_new_msg", "No new messages to summarize."),
                msg_type="info"
            )
            return

        config_user = self.configuration_settings.load_configuration()
        char_data_root = self.char_config["character_list"][self.character_name]
        selected_persona = char_data_root.get("selected_persona", "None")
        user_name = config_user.get("user_data", {}).get("personas", {}).get(selected_persona, {}).get("user_name", "User")

        async def run_generation():
            self.generate_btn.setEnabled(False)
            self.save_btn.setEnabled(False)
            self.clear_btn.setEnabled(False)
            self.generate_btn.setText(self.translations.get("summary_editor_generating", "GENERATING..."))

            old_text = self.summary_edit.toPlainText().strip()
            self.summary_edit.clear()

            generation_successful = False

            try:
                provider = AIFactory.get_provider(self.conversation_method)
                if not provider:
                    logger.error(f"Cannot perform auto-summary: Provider '{self.conversation_method}' not found.")
                    return

                summary_messages = self.prompt_engine.build_summary_prompt_blocks(
                    old_text, new_messages_chunk, self.character_name, user_name
                )

                async for chunk in provider.generate_summary(summary_messages):
                    self.summary_edit.insertPlainText(chunk)
                    scrollbar = self.summary_edit.verticalScrollBar()
                    scrollbar.setValue(scrollbar.maximum())

                generation_successful = True

            except Exception as e:
                sow_toast(
                    parent=self,
                    title=self.translations.get("error_title", "Error"),
                    text=f"Summarization failed:\n{str(e)}",
                    msg_type="error"
                )
                self.summary_edit.setPlainText(old_text)

            finally:
                self.generate_btn.setEnabled(True)
                self.save_btn.setEnabled(True)
                self.clear_btn.setEnabled(True)
                self.generate_btn.setText(self.translations.get("summary_editor_generate", "GENERATE SUMMARY"))

                if generation_successful:
                    self.last_seq = highest_seq_in_chunk
                    self.status_label.setText(self._get_status_text())
                    self.chat_data["last_summarized_sequence"] = highest_seq_in_chunk
                    self.configuration_characters.save_configuration_edit(self.char_config)
                    self.save_all()

        asyncio.create_task(run_generation())

class ImageGenSettingsDialog(QDialog):
    _BG       = "#0D0D12"
    _SURF1    = "#121218"
    _SURF2    = "#191922"
    _SURF3    = "#20202B"
    _TEXT     = "#DEDAD2"
    _TEXT_S   = "#6F6B63"
    _BORDER   = "rgba(255,255,255,0.055)"
    _BORDER_M = "rgba(255,255,255,0.10)"
    
    _BLUE     = "#4BB8FF"  
    _BLUE_MUT = "rgba(75, 184, 255, 0.15)"
    _BLUE_GLO = "rgba(75, 184, 255, 0.35)"
    _BLUE_BRT = "#82CDFF"

    _DANGER   = "#C44040"  
    _DNG_MUT  = "rgba(196,64,64,0.11)"
    _DNG_GLO  = "rgba(196,64,64,0.25)"

    def __init__(self, translations, configuration_settings, configuration_api, main_window, parent=None):
        super().__init__(parent)
        self.translations = translations
        self.configuration_settings = configuration_settings
        self.configuration_api = configuration_api
        self.main_window = main_window

        self.setWindowTitle(self.translations.get("image_gen_editor_title", "Image Generation Settings"))
        self.setWindowIcon(QIcon("app/gui/icons/logotype.ico"))
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        
        self.setMinimumSize(860, 540)
        self.resize(860, 540)

        self._init_fonts()
        self._apply_base_palette()
        self.setup_ui()
        self._setup_logic()

    def _init_fonts(self):
        def mf(size, weight=QFont.Weight.Normal):
            f = QFont("Inter Tight", size, weight)
            f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            return f

        self.f_title = mf(13, QFont.Weight.Bold)
        self.f_label = mf(8,  QFont.Weight.Bold)
        self.f_input = mf(10, QFont.Weight.Medium)
        self.f_btn   = mf(10, QFont.Weight.DemiBold)

    def _apply_base_palette(self):
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor(self._BG))
        self.setPalette(pal)
        self.setAutoFillBackground(True)

        self.setStyleSheet(
            f"QDialog {{ background-color: {self._BG}; }}"
            f"QLabel {{ border: none; background: transparent; color: {self._TEXT}; }}"
        )

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_toolbar())

        body = QWidget()
        body.setStyleSheet("background: transparent;")
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(24, 20, 24, 20)
        body_lay.setSpacing(20)

        left_col = QVBoxLayout()
        left_col.setSpacing(12)

        self.chk_enable = QtWidgets.QCheckBox(self.translations.get("image_gen_enable", "Enable Image Generation"))
        self.chk_enable.setFont(self.f_btn)
        self.chk_enable.setChecked(self.configuration_settings.get_main_setting("image_gen_enabled") or False)
        self.chk_enable.setStyleSheet(
            f"QCheckBox {{ color: {self._TEXT}; spacing: 10px; border: none; background: transparent; }}"
            f"QCheckBox::indicator {{ width: 18px; height: 18px; border: 1px solid {self._BORDER}; border-radius: 4px; background-color: {self._SURF2}; }}"
            f"QCheckBox::indicator:checked {{ background-color: {self._BLUE_MUT}; border-color: {self._BLUE_GLO}; }}"
        )
        left_col.addWidget(self.chk_enable)

        left_col.addWidget(self._build_card_label(self.translations.get("image_gen_grp_connection", "CONNECTION SETTINGS")))
        
        conn_card = QFrame()
        conn_card.setObjectName("conn_card")
        conn_card.setStyleSheet(self._s_card_style("conn_card"))
        conn_lay = QtWidgets.QFormLayout(conn_card)
        conn_lay.setContentsMargins(16, 16, 16, 16)
        conn_lay.setSpacing(12)

        self.cb_provider = QComboBox()
        self.cb_provider.setObjectName("IGProviderCombo")
        self.cb_provider.setFont(self.f_input)
        self.cb_provider.addItems(["Automatic1111", "ComfyUI (A1111 API)", "DALL-E 3", "NovelAI", "FLUX"])
        current_prov = self.configuration_settings.get_main_setting("image_provider") or "Automatic1111"
        self.cb_provider.setCurrentText(current_prov)
        self.cb_provider.setStyleSheet(self._s_combo("IGProviderCombo"))

        self.le_url = QLineEdit()
        self.le_url.setObjectName("IGApiUrlEdit")
        self.le_url.setFont(self.f_input)
        self.le_url.setText(self.configuration_settings.get_main_setting("image_api_url") or "http://127.0.0.1:7860")
        self.le_url.setPlaceholderText("http://127.0.0.1:7860")
        self.le_url.setStyleSheet(self._s_input("IGApiUrlEdit"))

        self.le_api_key = QLineEdit()
        self.le_api_key.setObjectName("IGApiKeyEdit")
        self.le_api_key.setFont(self.f_input)
        self.le_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.le_api_key.setPlaceholderText(self.translations.get("image_gen_api_key_placeholder", "Enter API Key here..."))
        self.le_api_key.setStyleSheet(self._s_input("IGApiKeyEdit"))
        
        self.lbl_api_key = QLabel(self.translations.get("image_gen_api_key", "API Key:"))
        self.lbl_api_key.setFont(self.f_input)
        self.lbl_api_key.setStyleSheet(f"color: {self._TEXT_S}; border: none;")

        lbl_prov = QLabel(self.translations.get("image_gen_provider", "Provider:"))
        lbl_prov.setStyleSheet(f"color: {self._TEXT_S}; border: none;"); lbl_prov.setFont(self.f_input)
        lbl_url = QLabel(self.translations.get("image_gen_api_url", "API URL (Local only):"))
        lbl_url.setStyleSheet(f"color: {self._TEXT_S}; border: none;"); lbl_url.setFont(self.f_input)

        conn_lay.addRow(lbl_prov, self.cb_provider)
        conn_lay.addRow(lbl_url, self.le_url)
        conn_lay.addRow(self.lbl_api_key, self.le_api_key)
        left_col.addWidget(conn_card)

        warning_card = QFrame()
        warning_card.setObjectName("warning_card")
        warning_card.setStyleSheet(
            f"QFrame#warning_card {{"
            f"  background-color: {self._DNG_MUT};"
            f"  border: 1px solid {self._DNG_GLO};"
            f"  border-radius: 8px;"
            f"}}"
            f"QLabel {{ border: none; background: transparent; }}"
        )
        warn_lay = QVBoxLayout(warning_card)
        warn_lay.setContentsMargins(14, 10, 14, 10)
        
        warning_lbl = QLabel(self.translations.get("image_gen_warning", "⚠ Warning: Running Local LLM + Local Image Gen simultaneously requires high VRAM. You may encounter Out-of-Memory crashes if your GPU lacks capacity."))
        warning_lbl.setFont(self.f_input)
        warning_lbl.setStyleSheet(f"color: {self._DANGER}; font-style: italic; line-height: 1.3;")
        warning_lbl.setWordWrap(True)
        warn_lay.addWidget(warning_lbl)
        
        left_col.addWidget(warning_card)
        left_col.addStretch()
        body_lay.addLayout(left_col, stretch=1)

        right_col = QVBoxLayout()
        right_col.setSpacing(12)

        right_col.addWidget(self._build_card_label(self.translations.get("image_gen_grp_prompts", "PROMPT INJECTION")))

        prompt_card = QFrame()
        prompt_card.setObjectName("prompt_card")
        prompt_card.setStyleSheet(self._s_card_style("prompt_card"))
        prompt_lay = QVBoxLayout(prompt_card)
        prompt_lay.setContentsMargins(16, 16, 16, 16)
        prompt_lay.setSpacing(8)

        lbl_prefix = QLabel(self.translations.get("image_gen_prefix", "Prefix Prompt (always added):"))
        lbl_prefix.setFont(self.f_input)
        lbl_prefix.setStyleSheet(f"color: {self._TEXT_S};")
        
        self.le_prefix = QLineEdit()
        self.le_prefix.setObjectName("IGPrefixEdit")
        self.le_prefix.setFont(self.f_input)
        self.le_prefix.setText(self.configuration_settings.get_main_setting("image_prefix_prompt") or "masterpiece, best quality")
        self.le_prefix.setStyleSheet(self._s_input("IGPrefixEdit"))
        
        lbl_neg = QLabel(self.translations.get("image_gen_negative", "Negative Prompt:"))
        lbl_neg.setFont(self.f_input)
        lbl_neg.setStyleSheet(f"color: {self._TEXT_S};")
        
        self.le_neg = QLineEdit()
        self.le_neg.setObjectName("IGNegEdit")
        self.le_neg.setFont(self.f_input)
        self.le_neg.setText(self.configuration_settings.get_main_setting("image_negative_prompt") or "worst quality, bad anatomy, bad hands, blurry")
        self.le_neg.setStyleSheet(self._s_input("IGNegEdit"))

        prompt_lay.addWidget(lbl_prefix)
        prompt_lay.addWidget(self.le_prefix)
        prompt_lay.addWidget(lbl_neg)
        prompt_lay.addWidget(self.le_neg)
        right_col.addWidget(prompt_card)

        right_col.addWidget(self._build_card_label(self.translations.get("image_gen_grp_dimensions", "GENERATION PARAMETERS")))

        dim_card = QFrame()
        dim_card.setObjectName("dim_card")
        dim_card.setStyleSheet(self._s_card_style("dim_card"))
        dim_lay = QHBoxLayout(dim_card)
        dim_lay.setContentsMargins(16, 16, 16, 16)
        dim_lay.setSpacing(12)

        w_col, self.sb_width = self._create_spinbox_column(
            self.translations.get("image_gen_width", "Width:"), 
            256, 2048, 64, int(self.configuration_settings.get_main_setting("image_width") or 512)
        )
        h_col, self.sb_height = self._create_spinbox_column(
            self.translations.get("image_gen_height", "Height:"), 
            256, 2048, 64, int(self.configuration_settings.get_main_setting("image_height") or 768)
        )
        s_col, self.sb_steps = self._create_spinbox_column(
            self.translations.get("image_gen_steps", "Steps:"), 
            1, 150, 1, int(self.configuration_settings.get_main_setting("image_steps") or 20)
        )

        dim_lay.addLayout(w_col)
        dim_lay.addLayout(h_col)
        dim_lay.addLayout(s_col)
        right_col.addWidget(dim_card)
        right_col.addStretch()

        body_lay.addLayout(right_col, stretch=1)
        root.addWidget(body, 1)

        root.addWidget(self._build_footer())

    def _build_toolbar(self):
        bar = QFrame()
        bar.setObjectName("IGToolbar")
        bar.setFixedHeight(56)
        bar.setStyleSheet(
            "QFrame#IGToolbar {"
            f"  background: {self._SURF1};"
            f"  border-bottom: 1px solid {self._BORDER};"
            "}"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(12)

        title_lbl = QLabel(self.translations.get("image_gen_editor_title", "IMAGE GEN ENGINE"))
        title_lbl.setFont(self.f_title)
        title_lbl.setStyleSheet(f"color: {self._TEXT}; border: none;")

        sep = QFrame()
        sep.setFixedSize(1, 24)
        sep.setStyleSheet(f"background: {self._BORDER};")

        sub_lbl = QLabel(self.translations.get("image_gen_subtitle", "LOCAL & CLOUD DIFFUSION"))
        sub_lbl.setFont(self.f_label)
        sub_lbl.setStyleSheet(f"color: {self._TEXT_S}; letter-spacing: 1.1px; border: none;")

        lay.addWidget(title_lbl)
        lay.addWidget(sep)
        lay.addWidget(sub_lbl)
        lay.addStretch()
        return bar

    def _build_footer(self):
        bar = QFrame()
        bar.setObjectName("IGFooter")
        bar.setFixedHeight(64)
        bar.setStyleSheet(
            "QFrame#IGFooter {"
            f"  background: {self._SURF1};"
            f"  border-top: 1px solid {self._BORDER};"
            "}"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 24, 0)
        lay.setSpacing(12)

        lay.addStretch()

        btn_cancel = QPushButton(self.translations.get("personas_editor_close", "CANCEL"))
        btn_cancel.setObjectName("IGBtnCancel")
        btn_cancel.setFixedSize(110, 36)
        btn_cancel.setFont(self.f_btn)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(
            f"QPushButton#IGBtnCancel {{"
            f"  background: transparent;"
            f"  border: 1px solid {self._BORDER};"
            f"  border-radius: 6px;"
            f"  color: {self._TEXT_S};"
            f"  letter-spacing: 0.5px;"
            f"}}"
            f"QPushButton#IGBtnCancel:hover {{"
            f"  background: {self._SURF2};"
            f"  border-color: {self._BORDER_M};"
            f"  color: {self._TEXT};"
            f"}}"
        )
        btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton(self.translations.get("image_gen_save", "SAVE SETTINGS"))
        self.btn_save.setObjectName("IGBtnSave")
        self.btn_save.setFixedSize(160, 36)
        self.btn_save.setFont(self.f_btn)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setStyleSheet(
            f"QPushButton#IGBtnSave {{"
            f"  background: {self._BLUE_MUT};"
            f"  border: 1px solid {self._BLUE_GLO};"
            f"  border-radius: 6px;"
            f"  color: {self._BLUE};"
            f"  letter-spacing: 0.5px;"
            f"}}"
            f"QPushButton#IGBtnSave:hover {{"
            f"  background: rgba(75, 184, 255, 0.25);"
            f"  border-color: rgba(75, 184, 255, 0.55);"
            f"  color: {self._BLUE_BRT};"
            f"}}"
        )
        self.btn_save.clicked.connect(self._save_and_close)

        lay.addWidget(btn_cancel)
        lay.addWidget(self.btn_save)

        return bar

    def _build_card_label(self, text):
        lbl = QLabel(text)
        lbl.setFont(self.f_label)
        lbl.setStyleSheet(f"color: {self._TEXT_S}; letter-spacing: 0.8px; margin-top: 4px; border: none;")
        return lbl

    def _s_card_style(self, card_id):
        return (
            f"QFrame#{card_id} {{"
            f"  background: {self._SURF1};"
            f"  border: 1px solid {self._BORDER};"
            f"  border-radius: 8px;"
            f"}}"
            f"QFrame#{card_id} QLabel {{"
            f"  border: none;"
            f"  background: transparent;"
            f"}}"
        )

    def _s_input(self, name):
        return (
            f"QWidget#{name} {{"
            f"  background: {self._SURF2};"
            f"  border: 1px solid {self._BORDER};"
            f"  border-radius: 6px;"
            f"  color: {self._TEXT};"
            f"  padding: 8px 10px;"
            f"  selection-background-color: {self._BLUE_MUT};"
            f"}}"
            f"QWidget#{name}:focus {{"
            f"  border-color: {self._BORDER_M};"
            f"  background: {self._SURF3};"
            f"}}"
        )

    def _s_combo(self, name):
        return (
            f"QComboBox#{name} {{"
            f"  background-color: {self._SURF2};"
            f"  color: {self._TEXT};"
            f"  border: 1px solid {self._BORDER};"
            f"  border-radius: 6px;"
            f"  padding-left: 10px;"
            f"  height: 34px;"
            f"}}"
            f"QComboBox#{name}:hover {{"
            f"  border-color: {self._BORDER_M};"
            f"}}"
            f"QComboBox#{name}::drop-down {{"
            f"  border: none;"
            f"  width: 24px;"
            f"}}"
            f"QComboBox#{name}::down-arrow {{"
            f"  width: 0; height: 0;"
            f"  border-left: 4px solid transparent;"
            f"  border-right: 4px solid transparent;"
            f"  border-top: 5px solid {self._TEXT_S};"
            f"}}"
            f"QComboBox#{name} QAbstractItemView {{"
            f"  background-color: {self._SURF3};"
            f"  color: {self._TEXT};"
            f"  border: 1px solid {self._BORDER_M};"
            f"  border-radius: 6px;"
            f"  padding: 4px;"
            f"  outline: none;"
            f"  selection-background-color: {self._SURF2};"
            f"}}"
        )

    def _create_spinbox_column(self, label_text, min_v, max_v, step, default_v):
        col = QVBoxLayout()
        col.setSpacing(6)
        col.setContentsMargins(0, 0, 0, 0)
        
        lbl = QLabel(label_text)
        lbl.setFont(self.f_input)
        lbl.setStyleSheet(f"color: {self._TEXT_S}; border: none;")
        
        sb = QSpinBox()
        sb.setFont(self.f_input)
        sb.setRange(min_v, max_v)
        sb.setSingleStep(step)
        sb.setValue(default_v)
        sb.setFixedHeight(34)
        sb.setStyleSheet(
            f"QSpinBox {{"
            f"  background: {self._SURF2};"
            f"  border: 1px solid {self._BORDER};"
            f"  border-radius: 6px;"
            f"  color: {self._TEXT};"
            f"  padding: 0 8px;"
            f"}}"
            f"QSpinBox:focus {{ border-color: {self._BORDER_M}; background: {self._SURF3}; }}"
            f"QSpinBox::up-button, QSpinBox::down-button {{ width: 0; }}"  
        )
        
        col.addWidget(lbl)
        col.addWidget(sb)
        return col, sb

    def _setup_logic(self):
        self.cb_provider.currentTextChanged.connect(self._update_api_key_visibility)
        self.le_api_key.textChanged.connect(self._save_api_key_realtime)
        self._update_api_key_visibility()

    def _update_api_key_visibility(self):
        prov = self.cb_provider.currentText()
        if prov in ["Automatic1111", "ComfyUI (A1111 API)", "DALL-E 3"]:
            self.lbl_api_key.hide()
            self.le_api_key.hide()
        else:
            self.lbl_api_key.show()
            self.le_api_key.show()
            token_key = f"{prov.upper()}_API_TOKEN"
            token = self.configuration_api.get_token(token_key)
            self.le_api_key.blockSignals(True)
            self.le_api_key.setText(token if token else "")
            self.le_api_key.blockSignals(False)

        if prov == "ComfyUI (A1111 API)":
            self.le_url.setPlaceholderText("http://127.0.0.1:8188")
            if self.le_url.text() == "http://127.0.0.1:7860" or not self.le_url.text():
                self.le_url.setText("http://127.0.0.1:8188")
        elif prov == "Automatic1111":
            self.le_url.setPlaceholderText("http://127.0.0.1:7860")
            if self.le_url.text() == "http://127.0.0.1:8188" or not self.le_url.text():
                self.le_url.setText("http://127.0.0.1:7860")

    def _save_api_key_realtime(self, text):
        prov = self.cb_provider.currentText()
        if prov not in ["Automatic1111", "ComfyUI (A1111 API)", "DALL-E 3"]:
            token_key = f"{prov.upper()}_API_TOKEN"
            self.configuration_api.save_api_token(token_key, text)

    def _save_and_close(self):
        self.configuration_settings.update_main_setting("image_gen_enabled", self.chk_enable.isChecked())
        self.configuration_settings.update_main_setting("image_provider", self.cb_provider.currentText())
        self.configuration_settings.update_main_setting("image_api_url", self.le_url.text().strip())
        self.configuration_settings.update_main_setting("image_prefix_prompt", self.le_prefix.text().strip())
        self.configuration_settings.update_main_setting("image_negative_prompt", self.le_neg.text().strip())
        self.configuration_settings.update_main_setting("image_width", self.sb_width.value())
        self.configuration_settings.update_main_setting("image_height", self.sb_height.value())
        self.configuration_settings.update_main_setting("image_steps", self.sb_steps.value())
        self.accept()

class Live2DMotionLinkerDialog(QDialog):
    """
    Dialog window for mapping each of the 28 emotions to a specific Live2D motion group.
    """
    def __init__(self, character_name, model_folder, translations, parent=None):
        super().__init__(parent)
        self.character_name = character_name
        self.model_folder = model_folder
        self.translations = translations
        self.configuration_characters = configuration.ConfigurationCharacters()
        
        self.setWindowTitle(f"Motion Mapper — {character_name}")
        self.setMinimumSize(540, 680)
        self.resize(560, 700)
        self.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        
        font_lbl = QtGui.QFont()
        font_lbl.setFamily("Inter Tight")
        font_lbl.setPointSize(9)
        font_lbl.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0c0c10, stop:0.5 #111118, stop:1 #16161d);
            }
            QLabel {
                color: #DEDAD2;
                font-family: 'Comfortaa', 'Segoe UI', sans-serif;
            }
            QScrollArea {
                background: transparent;
                border: none;
            }
            QComboBox {
                background-color: rgba(22, 22, 26, 0.6);
                color: #DEDAD2;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 6px 12px;
                font-family: 'Segoe UI', sans-serif;
            }
            QComboBox:hover {
                border-color: rgba(255, 255, 255, 0.2);
            }
            QComboBox QAbstractItemView {
                background-color: #121218;
                color: #DEDAD2;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                selection-background-color: rgba(255, 255, 255, 0.1);
                outline: none;
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #DEDAD2;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 8px 16px;
                font-family: 'Inter Tight SemiBold', sans-serif;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.12);
                border-color: rgba(255, 255, 255, 0.25);
                color: white;
            }
        """)
        
        self.motion_groups = self.get_motion_groups()
        self.saved_mapping = self.load_mapping()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(12)
        
        title = QLabel(self.translations.get("motion_mapper_title", "Live2D Motion Mapper"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")
        layout.addWidget(title)
        
        desc = QLabel(self.translations.get("motion_mapper_desc", "Assign a specific body animation group to each of the 28 detected emotions."))
        desc.setStyleSheet("font-size: 12px; color: #6F6B63; margin-bottom: 10px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 10, 0)
        scroll_layout.setSpacing(8)
        
        self.combos = {}
        
        emotions = [
            "admiration", "amusement", "anger", "annoyance", "approval", "caring", "confusion", "curiosity",
            "desire", "disappointment", "disapproval", "disgust", "embarrassment", "excitement", "fear",
            "gratitude", "grief", "love", "nervousness", "neutral", "optimism", "pride", "realization",
            "relief", "remorse", "surprise", "joy", "sadness"
        ]
        
        emojis = {
            "admiration": "🤩",     "amusement": "😆",      "anger": "😡",
            "annoyance": "😒",      "approval": "👍",       "caring": "🥰",
            "confusion": "😕",      "curiosity": "🤔",      "desire": "😏",
            "disappointment": "😞",   "disapproval": "👎",    "disgust": "🤢",
            "embarrassment": "😳",  "excitement": "🎉",      "fear": "😨",
            "gratitude": "🙏",      "grief": "😭",           "love": "❤️",
            "nervousness": "😰",    "neutral": "😐",        "optimism": "☀️",
            "pride": "😎",          "realization": "💡",     "relief": "😌",
            "remorse": "😔",        "surprise": "😲",       "joy": "😊",
            "sadness": "😢"
        }
        
        for emo in emotions:
            row = QHBoxLayout()
            row.setSpacing(10)
            
            emoji_lbl = QLabel(emojis.get(emo, "✨"))
            emoji_lbl.setFont(QtGui.QFont("Segoe UI Emoji", 12))
            emoji_lbl.setFixedWidth(24)
            
            emo_lbl = QLabel(emo.capitalize())
            emo_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: rgba(255,255,255,0.85);")
            
            combo = QComboBox()
            combo.setFixedHeight(34)
            combo.setFixedWidth(220)
            
            combo.addItem("Default fallback", userData="default")
            for mg in self.motion_groups:
                display_name = f"🎬 {mg}" if mg else "🎬 [Unlabeled]"
                combo.addItem(display_name, userData=mg)
            combo.addItem("🚫 None / Silent", userData="none")
            
            mapped_val = self.saved_mapping.get(emo)
            if mapped_val == "none":
                combo.setCurrentIndex(combo.count() - 1)
            elif mapped_val is not None:
                found = False
                for i in range(combo.count()):
                    if combo.itemData(i) == mapped_val:
                        combo.setCurrentIndex(i)
                        found = True
                        break
                if not found:
                    combo.setCurrentIndex(0)
            else:
                combo.setCurrentIndex(0)
                
            self.combos[emo] = combo
            
            row.addWidget(emoji_lbl)
            row.addWidget(emo_lbl, 1)
            row.addWidget(combo)
            scroll_layout.addLayout(row)
            
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)
        
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        
        btn_reset = QPushButton(self.translations.get("reset_def_btn", "Reset Defaults"))
        btn_reset.setFont(font_lbl)
        btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset.clicked.connect(self.reset_to_defaults)
        
        btn_cancel = QPushButton(self.translations.get("cancel", "Cancel"))
        btn_cancel.setFont(font_lbl)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        
        btn_save = QPushButton(self.translations.get("save_mapping_btn", "Save Mapping"))
        btn_save.setFont(font_lbl)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet("""
            QPushButton {
                background: rgba(75, 184, 255, 0.12);
                border: 1px solid rgba(75, 184, 255, 0.25);
                color: #4BB8FF;
            }
            QPushButton:hover {
                background: rgba(75, 184, 255, 0.25);
                border-color: rgba(75, 184, 255, 0.55);
                color: #82CDFF;
            }
        """)
        btn_save.clicked.connect(self.save_mapping)
        
        btn_row.addWidget(btn_reset)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)
        
    def find_model_json(self, live2d_model_folder):
        for root, dirs, files in os.walk(live2d_model_folder):
            for file in files:
                if file.endswith(".model3.json"):
                    return os.path.join(root, file)
        return None

    def get_motion_groups(self) -> list[str]:
        try:
            model_json_path = self.find_model_json(self.model_folder)
            if not model_json_path or not os.path.exists(model_json_path):
                return []
            with open(model_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            motions_dict = data.get("FileReferences", {}).get("Motions", {})
            return list(motions_dict.keys())
        except Exception as e:
            logger.debug(f"Failed to parse motion groups: {e}")
            return []

    def load_mapping(self) -> dict:
        config = self.configuration_characters.load_configuration()
        char_info = config.get("character_list", {}).get(self.character_name, {})
        return char_info.get("emotion_motions", {})

    def reset_to_defaults(self):
        for emo, combo in self.combos.items():
            combo.setCurrentIndex(0)
           
    def save_mapping(self):
        mapping = {}
        for emo, combo in self.combos.items():
            mapped_val = combo.itemData(combo.currentIndex())
            if mapped_val != "default":
                mapping[emo] = mapped_val

        config = self.configuration_characters.load_configuration()
        if "character_list" in config and self.character_name in config["character_list"]:
            config["character_list"][self.character_name]["emotion_motions"] = mapping
            self.configuration_characters.save_configuration_edit(config)
            sow_toast(self, "Success", "Emotion-to-Motion mapping saved successfully!", "success")
            self.accept()

class StatusDot(QtWidgets.QWidget):
    def __init__(self, parent=None, dot_size=8, box_size=20):
        super().__init__(parent)
        self._dot_size = dot_size
        self._color = QtGui.QColor(255, 255, 255, 140)
        self._glow = 0.22
        self._pulse_anim = None
        self.setFixedSize(box_size, box_size)

    def get_color(self):
        return self._color

    def set_color(self, color):
        self._color = color
        self.update()

    color = QtCore.pyqtProperty(QtGui.QColor, get_color, set_color)

    def get_glow(self):
        return self._glow

    def set_glow(self, value):
        self._glow = value
        self.update()

    glow = QtCore.pyqtProperty(float, get_glow, set_glow)

    def start_pulse(self):
        if self._pulse_anim and self._pulse_anim.state() == QtCore.QAbstractAnimation.State.Running:
            return
        self._pulse_anim = QtCore.QPropertyAnimation(self, b"glow", self)
        self._pulse_anim.setDuration(1400)
        self._pulse_anim.setStartValue(0.22)
        self._pulse_anim.setKeyValueAt(0.5, 0.65)
        self._pulse_anim.setEndValue(0.22)
        self._pulse_anim.setEasingCurve(QtCore.QEasingCurve.Type.InOutSine)
        self._pulse_anim.setLoopCount(-1)
        self._pulse_anim.start()

    def stop_pulse(self):
        if self._pulse_anim:
            self._pulse_anim.stop()
            self._pulse_anim = None
        self.set_glow(0.22)

    @safe_paint
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2
        cy = self.height() / 2
        core_r = self._dot_size / 2
        halo_r = core_r * (1.4 + self._glow * 1.6)

        halo_color = QtGui.QColor(self._color)
        halo_color.setAlphaF(min(self._color.alphaF() * (0.35 + self._glow * 0.5), 0.7))
        painter.setBrush(halo_color)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawEllipse(QtCore.QPointF(cx, cy), halo_r, halo_r)

        painter.setBrush(self._color)
        painter.drawEllipse(QtCore.QPointF(cx, cy), core_r, core_r)

class LocalModelStatusWidget(QtWidgets.QWidget):
    STYLES = {
        "offline": {
            "color": QtGui.QColor(255, 255, 255, 64),
            "text_color": "rgba(255, 255, 255, 0.3)",
            "pulse": False,
            "key": "local_model_state_offline",
            "default": "MODEL OFFLINE",
        },
        "loading": {
            "color": QtGui.QColor(0xE8, 0xA0, 0x40),
            "text_color": "#E8A040",
            "pulse": True,
            "key": "local_model_state_connecting",
            "default": "LOADING MODEL...",
        },
        "generating": {
            "color": QtGui.QColor(0x3B, 0x82, 0xF6),
            "text_color": "#3B82F6",
            "pulse": True,
            "key": "local_model_state_generating",
            "default": "GENERATING...",
        },
        "online": {
            "color": QtGui.QColor(0x22, 0xC5, 0x5E),
            "text_color": "#22C55E",
            "pulse": False,
            "key": "local_model_state_online",
            "default": "MODEL READY",
        },
    }

    def __init__(self, parent=None, translations=None):
        super().__init__(parent)
        self.translations = translations or (lambda key, default: default)
        self._color_anim = None
 
        self.setMinimumSize(QtCore.QSize(190, 24))
        self.setMaximumSize(QtCore.QSize(190, 24))
        self.setStyleSheet("background: transparent; border: none;")
 
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(13, 0, 18, 0)
        layout.setSpacing(8)
 
        self.status_dot = StatusDot(parent=self)

        first_model_status = self.translations.get("local_model_state_offline", "MODEL OFFLINE")

        self.status_text = QtWidgets.QLabel(first_model_status, parent=self)
        font_status_text = QtGui.QFont("Inter Tight SemiBold", 8)
        font_status_text.setLetterSpacing(QtGui.QFont.SpacingType.AbsoluteSpacing, 0.6)
        font_status_text.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.status_text.setFont(font_status_text)
        self.status_text.setStyleSheet(
            f"color: {self.STYLES['offline']['text_color']}; background: transparent; border: none;"
        )
 
        layout.addWidget(self.status_dot)
        layout.addWidget(self.status_text)
        layout.addStretch()

    def set_system_status(self, status_type):
        style = self.STYLES.get(status_type)
        if style is None:
            return

        self.status_text.setText(self.translations.get(style["key"], style["default"]))
        self.status_text.setStyleSheet(
            f"color: {style['text_color']}; background: transparent; border: none;"
        )

        if self._color_anim:
            self._color_anim.stop()

        self._color_anim = QtCore.QPropertyAnimation(self.status_dot, b"color", self.status_dot)
        self._color_anim.setDuration(220)
        self._color_anim.setStartValue(self.status_dot.color)
        self._color_anim.setEndValue(style["color"])
        self._color_anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self._color_anim.start()

        if style["pulse"]:
            self.status_dot.start_pulse()
        else:
            self.status_dot.stop_pulse()

class SceneFolderCard(QtWidgets.QFrame):
    def __init__(self, group_name: str, scene_count: int, preview_bgs: list, soul_stage_page, parent=None):
        super().__init__(parent)
        self.setFixedSize(210, 270)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

        self.group_name = group_name
        self.scene_count = scene_count
        self.soul_stage_page = soul_stage_page
        self.translations = getattr(soul_stage_page, "translations", {}) or _load_translations()
        
        self.pixmap = QtGui.QPixmap(210, 270)
        self.pixmap.fill(QtCore.Qt.GlobalColor.transparent)
        
        painter = QtGui.QPainter(self.pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        
        valid_bgs = [bg for bg in preview_bgs if bg and bg != "None" and os.path.exists(bg)]
        
        if valid_bgs:
            positions = [
                QtCore.QRectF(0, 0, 105, 135), QtCore.QRectF(105, 0, 105, 135),
                QtCore.QRectF(0, 135, 105, 135), QtCore.QRectF(105, 135, 105, 135)
            ]
            for i, path in enumerate(valid_bgs[:4]):
                px = QtGui.QPixmap(path)
                if px.isNull(): 
                    px = QtGui.QPixmap("app/gui/icons/soul_stage.png")
                
                scaled = px.scaled(105, 135, QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding, QtCore.Qt.TransformationMode.SmoothTransformation)
                sx = (scaled.width() - 105) // 2
                sy = (scaled.height() - 135) // 2
                cropped = scaled.copy(sx, sy, 105, 135)
                painter.drawPixmap(int(positions[i].x()), int(positions[i].y()), cropped)
            
            painter.fillRect(self.pixmap.rect(), QtGui.QColor(0, 0, 0, 110))
        else:
            gradient = QtGui.QLinearGradient(0, 0, 210, 270)
            gradient.setColorAt(0, QtGui.QColor(18, 36, 28))
            gradient.setColorAt(1, QtGui.QColor(10, 20, 15))
            painter.fillRect(self.pixmap.rect(), QtGui.QBrush(gradient))
            
            stage_icon = QtGui.QPixmap("app/gui/icons/soul_stage.png").scaled(
                52, 52, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation
            )
            painter.drawPixmap(210//2 - 26, 270//2 - 40, stage_icon)
            
        painter.end()

        self.shadow_effect = QtWidgets.QGraphicsDropShadowEffect(self)
        self.shadow_effect.setBlurRadius(18)
        self.shadow_effect.setColor(QtGui.QColor(0, 230, 118, 40))
        self.shadow_effect.setOffset(0, 5)
        self.setGraphicsEffect(self.shadow_effect)

        self._hover_scale = 1.0
        self.anim_scale = QtCore.QPropertyAnimation(self, b"hover_scale")
        self.anim_scale.setDuration(300)
        self.anim_scale.setEasingCurve(QtCore.QEasingCurve.Type.InOutCubic)

        self._darkness_alpha = 100.0
        self.anim_dark = QtCore.QPropertyAnimation(self, b"darkness_alpha")
        self.anim_dark.setDuration(300)
        self.anim_dark.setEasingCurve(QtCore.QEasingCurve.Type.InOutCubic)

        self._info_alpha = 255.0
        self.anim_info = QtCore.QPropertyAnimation(self, b"info_alpha")
        self.anim_info.setDuration(250)
        self.anim_info.setEasingCurve(QtCore.QEasingCurve.Type.InOutCubic)

        self.action_panel = QtWidgets.QFrame(self)
        self.action_panel.setStyleSheet("background-color: rgba(14, 20, 16, 0.95); border: 1px solid rgba(0, 230, 118, 0.2); border-radius: 15px;")
        self.action_panel.setGeometry(10, 280, 190, 45)
        self.action_panel_layout = QtWidgets.QHBoxLayout(self.action_panel)
        self.action_panel_layout.setContentsMargins(5, 0, 5, 0)
        self.action_panel_layout.setSpacing(5)
        
        self.panel_anim = QtCore.QPropertyAnimation(self.action_panel, b"pos")
        self.panel_anim.setDuration(300)
        self.panel_anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        
        self.edit_btn = AnimatedHoverButton("app/gui/icons/edit.png", "#00E676", self.translations.get("folder_edit_btn", "Edit Folder"))
        self.delete_btn = AnimatedHoverButton("app/gui/icons/bin.png", "#D32F2F", self.translations.get("folder_delete_btn", "Delete Folder"))
        
        self.edit_btn.clicked.connect(self._on_edit_clicked)
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        
        self.action_panel_layout.addWidget(self.edit_btn)
        self.action_panel_layout.addWidget(self.delete_btn)

    @QtCore.pyqtProperty(float)
    def hover_scale(self): return self._hover_scale
    @hover_scale.setter
    def hover_scale(self, value): self._hover_scale = value; self.update()

    @QtCore.pyqtProperty(float)
    def darkness_alpha(self): return self._darkness_alpha
    @darkness_alpha.setter
    def darkness_alpha(self, value): self._darkness_alpha = value; self.update()

    @QtCore.pyqtProperty(float)
    def info_alpha(self): return self._info_alpha
    @info_alpha.setter
    def info_alpha(self, value): self._info_alpha = value; self.update()

    def enterEvent(self, event):
        self.anim_scale.setEndValue(1.05)
        self.anim_dark.setEndValue(0.0)
        self.anim_info.setEndValue(0.0)
        self.panel_anim.setEndValue(QtCore.QPoint(10, 215))
        
        self.anim_scale.start()
        self.anim_dark.start()
        self.anim_info.start()
        self.panel_anim.start()

        self.shadow_effect.setOffset(0, 8)
        self.shadow_effect.setBlurRadius(25)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim_scale.setEndValue(1.0)
        self.anim_dark.setEndValue(100.0)
        self.anim_info.setEndValue(255.0)
        self.panel_anim.setEndValue(QtCore.QPoint(10, 280))
        
        self.anim_scale.start()
        self.anim_dark.start()
        self.anim_info.start()
        self.panel_anim.start()

        self.shadow_effect.setOffset(0, 5)
        self.shadow_effect.setBlurRadius(18)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.soul_stage_page._open_folder_view(self.group_name)
        super().mousePressEvent(event)

    def _on_edit_clicked(self):
        self.soul_stage_page._open_folder_editor(self.group_name)

    def _on_delete_clicked(self):
        title = self.translations.get("folder_delete_confirm_title", "Delete Folder")
        msg = self.translations.get("folder_delete_confirm_msg", "Delete this folder?")
        detail = f"'{self.group_name}' · " + self.translations.get("folder_delete_detail_scenes", "Scenes will return to the main lobby.")
        full_text = f"{msg}<br><span style='color: rgba(255,255,255,0.4); font-size: 9pt;'>{detail}</span>"

        dlg = SowConfirmDialog(
            parent=self.window(),
            title=title,
            text=full_text,
            confirm_text=self.translations.get("delete", "Delete"),
            danger=True
        )

        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            groups = self.soul_stage_page._get_scene_groups()
            groups.pop(self.group_name, None)
            self.soul_stage_page._save_scene_groups(groups)
            self.soul_stage_page.refresh_lobby()

    @safe_paint
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)

        rect = self.rect()
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(rect), 15, 15)
        painter.setClipPath(path)

        painter.save()
        scale_factor = max(rect.width() / self.pixmap.width(), rect.height() / self.pixmap.height())
        final_scale = scale_factor * self._hover_scale
        painter.translate(rect.center())
        painter.scale(final_scale, final_scale)
        painter.drawPixmap(-self.pixmap.width() // 2, -self.pixmap.height() // 2, self.pixmap)
        painter.restore()

        if self._darkness_alpha > 0:
            painter.fillRect(rect, QtGui.QColor(0, 0, 0, int(self._darkness_alpha)))

        if self._info_alpha > 0:
            gradient = QtGui.QLinearGradient(0, rect.height() * 0.4, 0, rect.height())
            gradient.setColorAt(0, QtGui.QColor(0, 0, 0, 0))
            gradient.setColorAt(1, QtGui.QColor(0, 0, 0, int(min(225, self._info_alpha))))
            painter.fillRect(rect, QtGui.QBrush(gradient))

            painter.setPen(QtGui.QColor(255, 255, 255, int(self._info_alpha)))
            font = QtGui.QFont("Inter Tight SemiBold", 13, QtGui.QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(QtCore.QRect(15, rect.height() - 75, rect.width() - 30, 30), 
                             QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter, 
                             self.group_name)
            
            scenes_label = self.translations.get("folder_scenes_label", "scenes")
            count_font = QtGui.QFont("Inter Tight Medium", 10)
            painter.setFont(count_font)
            painter.setPen(QtGui.QColor(0, 230, 118, int(self._info_alpha * 0.85)))
            count_text = f"🎬 {self.scene_count} {scenes_label}"
            painter.drawText(QtCore.QRect(15, rect.height() - 45, rect.width() - 30, 20), 
                             QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter, 
                             count_text)

        painter.end()
