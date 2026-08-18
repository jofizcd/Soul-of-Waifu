import os
import requests
import logging
import urllib.request
import ssl
import json
import time

from datetime import datetime, timedelta

from PyQt6 import QtCore, QtWidgets, QtGui
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QListWidget, QLabel, QDialog, 
    QVBoxLayout as QVBox, QListWidgetItem
)

from app.gui.custom_widgets import sow_toast, SowConfirmDialog

os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
from huggingface_hub import HfApi, hf_hub_download

logger = logging.getLogger("Models Hub Client")

class ModelSearch(QThread):
    """
    A thread-based class for searching GGUF models on Hugging Face Hub.
    
    Signals:
        progress (str, str, int): Emits model ID, author, and download count during search.
        finished (list): Emits the final list of relevant model IDs when search completes.
        error (str): Emits an error message if something goes wrong.
    """
    progress = pyqtSignal(str, str, int)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, query):
        super().__init__()
        self.query = query.strip()
        self.api = HfApi()

    def run(self):
        try:
            full_query = f"{self.query} gguf" if self.query else "gguf"
            models = list(self.api.list_models(
                search=full_query,
                limit=100,
                sort="downloads",
                direction=-1
            ))

            relevant_models = []

            for model in models:
                model_id = model.id
                info = self.api.model_info(model_id)

                author = info.author or "Unknown"
                downloads = info.downloads or 0

                relevant_models.append(model_id)

                self.progress.emit(model_id, author, downloads)

            self.finished.emit(relevant_models)

        except Exception as e:
            self.error.emit(str(e))

class ModelRecommendations(QThread):
    """
    A thread-based class for showing model recommendations from GitHub JSON.
    Downloads recommended_models.json from https://github.com/jofizcd/sow-data/raw/main/recommended_models.json
    and caches it locally for offline use.
    
    Signals:
        progress (str, str, int, str, bool): Emits model_id, author, downloads, compatibility_text, is_compatible
        finished (list): Emits the final list of model IDs when complete.
        error (str): Emits an error message if something goes wrong.
    """
    progress = pyqtSignal(str, str, int, str, bool)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    CURATED_MODELS_URL = "https://github.com/jofizcd/sow-data/raw/main/recommended_models.json"
    CACHE_FILE = "app/utils/ai_clients/backend/_temp/recommended_models_cache.json"
    CACHE_EXPIRY_HOURS = 24

    def __init__(self, available_ram_gb=8, has_gpu=False, gpu_vram_gb=0):
        super().__init__()
        self.available_ram_gb = available_ram_gb
        self.has_gpu = has_gpu
        self.gpu_vram_gb = gpu_vram_gb

    def run(self):
        try:
            curated_data = self.load_curated_models()
            models = curated_data.get("models", []) if curated_data else self.get_fallback_models()
            
            if not models:
                models = self.get_fallback_models()

            evaluated_models = []
            for model in models:
                model_id = model.get("hf_id", "")
                author = model.get("author", "Unknown")
                downloads = model.get("downloads", 0)
                compatibility_text, is_compatible = self.check_compatibility(model)
                
                evaluated_models.append({
                    "model_id": model_id,
                    "author": author,
                    "downloads": downloads,
                    "compatibility_text": compatibility_text,
                    "is_compatible": is_compatible,
                    "raw_model": model
                })

            evaluated_models.sort(
                key=lambda x: (
                    self.get_compatibility_priority(x["compatibility_text"])
                ),
                reverse=True
            )

            model_ids = []
            for item in evaluated_models:
                model_ids.append(item["model_id"])
                self.progress.emit(
                    item["model_id"], 
                    item["author"], 
                    item["downloads"], 
                    item["compatibility_text"], 
                    item["is_compatible"]
                )

            self.finished.emit(model_ids)

        except Exception as e:
            fallback_models = self.get_fallback_models()
            for model in fallback_models:
                model_id = model.get("hf_id", "")
                author = model.get("author", "Unknown")
                downloads = model.get("downloads", 0)
                compatibility_text, is_compatible = self.check_compatibility(model)
                self.progress.emit(model_id, author, downloads, compatibility_text, is_compatible)
            self.finished.emit([m["hf_id"] for m in fallback_models])
            self.error.emit(f"Error loading recommendations: {str(e)}")
    
    def load_curated_models(self):
        if self.should_update_cache():
            try:
                data = self.download_from_github()
                if data:
                    self.save_to_cache(data)
                    logger.info("Recommended models updated from GitHub")
                    return data
            except Exception as e:
                logger.warning(f"Failed to update from GitHub: {e}")
        
        cached_data = self.load_from_cache()
        if cached_data:
            logger.info("Using cached list of recommended models")
            return cached_data
        
        logger.warning("No data on recommended models (no cache and no internet)")
        return {"models": []}
    
    def download_from_github(self):
        try:
            context = ssl._create_unverified_context()
            with urllib.request.urlopen(self.CURATED_MODELS_URL, timeout=15, context=context) as response:
                data = response.read().decode('utf-8')
                return json.loads(data)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise Exception("curated_models.json not found on GitHub. Check the file path.")
            else:
                raise Exception(f"HTTP error {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise Exception(f"Network error: {str(e.reason)}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            raise Exception(f"Unknown error: {str(e)}")
    
    def save_to_cache(self, data):
        try:
            os.makedirs(os.path.dirname(self.CACHE_FILE), exist_ok=True)
            with open(self.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            timestamp_file = self.CACHE_FILE + ".timestamp"
            with open(timestamp_file, 'w', encoding='utf-8') as f:
                f.write(datetime.now().isoformat())
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
    
    def load_from_cache(self):
        try:
            if os.path.exists(self.CACHE_FILE):
                with open(self.CACHE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
        return None
    
    def should_update_cache(self):
        timestamp_file = self.CACHE_FILE + ".timestamp"
        
        if not os.path.exists(timestamp_file):
            return True
        
        try:
            with open(timestamp_file, 'r', encoding='utf-8') as f:
                timestamp_str = f.read().strip()
                last_update = datetime.fromisoformat(timestamp_str)
                
                expiry_time = timedelta(hours=self.CACHE_EXPIRY_HOURS)
                return datetime.now() - last_update > expiry_time
        except Exception as e:
            logger.warning(f"Cache timestamp check error: {e}")
            return True
    
    def check_compatibility(self, model):
        min_ram = model.get("min_ram_gb", 4)
        rec_ram = model.get("recommended_ram_gb", 8)
        min_vram = model.get("min_vram_gb", 0)
        rec_vram = model.get("recommended_vram_gb", 4)
        
        user_ram = self.available_ram_gb + 1
        
        if user_ram < min_ram:
            return f"❌ Minimum {min_ram} GB RAM required (you have {user_ram} GB)", False
        elif user_ram < rec_ram:
            return f"⚠️ Recommended {rec_ram} GB RAM (you have {user_ram} GB)", True
        elif self.has_gpu and self.gpu_vram_gb > 0:
            if self.gpu_vram_gb < min_vram:
                return f"⚠️ Full GPU loading requires {min_vram} GB VRAM (you have {self.gpu_vram_gb:.1f} GB)", True
            elif self.gpu_vram_gb < rec_vram:
                return f"✅ Will run (some layers on CPU, {self.gpu_vram_gb:.1f} GB VRAM)", True
            else:
                return f"✅ Fully loads into GPU ({self.gpu_vram_gb:.1f} GB VRAM)", True
        else:
            return f"✅ Will run on your PC", True

    def get_compatibility_priority(self, compatibility_text):
        if "❌" in compatibility_text:
            return 0
        if "⚠️" in compatibility_text:
            if "VRAM" in compatibility_text:
                return 2
            return 1
        if "✅" in compatibility_text:
            if "Fully loads into GPU" in compatibility_text:
                return 5
            if "some layers on CPU" in compatibility_text:
                return 4
            if "Will run on CPU" in compatibility_text:
                return 3
            return 3
        return 0
    
    def get_fallback_models(self):
        return [
            {
                "hf_id": "mradermacher/Famino-12B-Model_Stock-i1-GGUF",
                "name": "Famino-12B-Model_Stock",
                "author": "DreadPoor",
                "downloads": 145,
                "min_ram_gb": 8,
                "recommended_ram_gb": 12,
                "min_vram_gb": 0,
                "recommended_vram_gb": 10,
                "optimal_quant": "Q4_K_M",
                "description_en": "Famino-12B-Model_Stock is a high-quality 12B merge created using the Model Stock method on base DreadPoor/Ward-12B-Model_Stock, incorporating strong components like cgato/Nemo-12b-Humanize-SFT-v0.2.5-KTO, DreadPoor/Irix-12B-Model_Stock, redrix/GodSlayer-12B-ABYSS, and PygmalionAI/Pygmalion-3-12B. The model is widely regarded as one of the best in the 12B class for writing quality and usability: it delivers coherent, vivid prose, excellent narrative flow, high swipe usability, and strong performance in roleplay, creative writing, and adventure scenarios. Community feedback frequently highlights it as 'the highest ranked 12B in writing category on UGI', 'better than many 70B models in prose', 'really good at writing', and 'slightly edges out Irix in style'. It produces detailed, engaging text with minimal formatting issues or slop, making it especially suitable for immersive storytelling. GGUF quants (especially i1/imatrix from mradermacher) run comfortably on mid-range hardware (Q4_K_M ~10 GB VRAM). Use temperature 0.7–1.0 for optimal creativity and coherence. Often recommended alongside Irix-12B-Model_Stock as a top prose-focused 12B merge.",
                "description_ru": "Famino-12B-Model_Stock — это высококачественный 12B мерж, созданный методом Model Stock на базе DreadPoor/Ward-12B-Model_Stock с включением сильных компонентов: cgato/Nemo-12b-Humanize-SFT-v0.2.5-KTO, DreadPoor/Irix-12B-Model_Stock, redrix/GodSlayer-12B-ABYSS и PygmalionAI/Pygmalion-3-12B. Модель считается одной из лучших в 12B-классе по качеству письма и удобству: выдаёт последовательную, яркую прозу, отличный нарративный поток, высокую полезность свайпов и сильную работу в roleplay, креативности и adventure-сценариях. В сообществе часто называют 'высокооценненной моделью 12B в категории writing на UGI', 'лучше многих 70B по прозе', 'реально хороша в генерации текста' и 'чуть лучше Irix по стилю'. Производит детализированный, увлекательный текст с минимумом проблем форматирования или слопа — идеально для иммерсивного сторителлинга. GGUF-кванты (особенно i1/imatrix от mradermacher) комфортно работают на среднем железе (Q4_K_M ~10 ГБ VRAM). Используйте температуру 0.7–1.0 для лучшей креативности и связности. Часто рекомендуют вместе с Irix-12B-Model_Stock как топовый проза-ориентированный 12B-мердж.",
                "author_notes": "Merge method: Model Stock. Base: DreadPoor/Ward-12B-Model_Stock. Key components: Nemo-Humanize-SFT, Irix-12B, GodSlayer-ABYSS, Pygmalion-3-12B. GGUF quants: mradermacher (i1/imatrix recommended for highest quality). Temperature 0.7–1.0 suggested. Focus: exceptional prose, high swipe usability, coherent writing. Strong in roleplay and creative scenarios. Often compared favorably to Irix with slight edge in writing quality."
            }
        ]
        
class RecommendedModelItemWidget(QWidget):
    def __init__(self, model_id, author, downloads, compatibility_text, is_compatible, 
                 show_model_info_method, download_model_method, parent=None, 
                 download_button_translation=" Download model", 
                 author_label_translation="Author - ", 
                 downloads_label_translation="Downloads - ",
                 compatibility_label_translation="Compatibility: "):
        super().__init__(parent)
        
        self.model_id = model_id
        self.show_model_info_method = show_model_info_method
        self.is_compatible = is_compatible

        self.setFixedHeight(85)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 2, 5, 2) 
        main_layout.setSpacing(0)

        self.glass_card = QtWidgets.QFrame(self)
        self.glass_style_normal = """
            QFrame {
                background-color: rgba(25, 25, 30, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
            }
        """
        self.glass_style_hover = """
            QFrame {
                background-color: rgba(35, 35, 45, 0.65);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 16px;
            }
        """
        self.glass_card.setStyleSheet(self.glass_style_normal)

        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QtGui.QColor(0, 0, 0, 80))
        shadow.setOffset(0, 5)
        self.glass_card.setGraphicsEffect(shadow)

        card_layout = QHBoxLayout(self.glass_card)
        card_layout.setContentsMargins(12, 10, 12, 10) 
        card_layout.setSpacing(15)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)

        model_name = model_id.split("/")[-1]
        self.name_label = QLabel(model_name)
        font_name = QtGui.QFont("Inter Tight SemiBold", 12, QtGui.QFont.Weight.Bold)
        font_name.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.name_label.setFont(font_name)
        self.name_label.setStyleSheet("color: rgba(255, 255, 255, 0.95); background: transparent; border: none;")
        info_layout.addWidget(self.name_label)

        meta_row_layout = QHBoxLayout()
        meta_row_layout.setSpacing(8)

        badge_style = """
            QLabel {
                background-color: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
                font-family: 'Inter Tight Medium';
            }
        """

        self.author_label = QLabel(f"👤 {author_label_translation} {author}")
        font = QtGui.QFont()
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.author_label.setFont(font)
        self.author_label.setFixedHeight(20)
        self.author_label.setStyleSheet(badge_style)
        meta_row_layout.addWidget(self.author_label)

        self.downloads_label = QLabel(f"⬇️ {downloads_label_translation} {downloads}")
        font = QtGui.QFont()
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.downloads_label.setFont(font)
        self.downloads_label.setFixedHeight(20)
        self.downloads_label.setStyleSheet(badge_style)
        meta_row_layout.addWidget(self.downloads_label)

        self.compatibility_label = QLabel(f"{compatibility_label_translation} {compatibility_text}")
        font = QtGui.QFont()
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.compatibility_label.setFont(font)
        self.compatibility_label.setFixedHeight(20)
        
        if "✅" in compatibility_text:
            self.compatibility_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(76, 175, 80, 0.15);
                    color: #81C784;
                    border: 1px solid rgba(76, 175, 80, 0.3);
                    border-radius: 6px;
                    padding: 4px 8px;
                    font-size: 11px;
                    font-family: 'Inter Tight SemiBold';
                }
            """)
        elif "⚠️" in compatibility_text:
            self.compatibility_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(255, 152, 0, 0.15);
                    color: #FFB74D;
                    border: 1px solid rgba(255, 152, 0, 0.3);
                    border-radius: 6px;
                    padding: 4px 8px;
                    font-size: 11px;
                    font-family: 'Inter Tight SemiBold';
                }
            """)
        else:
            self.compatibility_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(244, 67, 54, 0.15);
                    color: #E57373;
                    border: 1px solid rgba(244, 67, 54, 0.3);
                    border-radius: 6px;
                    padding: 4px 8px;
                    font-size: 11px;
                    font-family: 'Inter Tight SemiBold';
                }
            """)
            
        meta_row_layout.addWidget(self.compatibility_label)
        meta_row_layout.addStretch()

        info_layout.addLayout(meta_row_layout)
        card_layout.addLayout(info_layout, stretch=1)

        self.btn_download = QPushButton(download_button_translation)
        font_btn = QtGui.QFont("Inter Tight SemiBold", 9)
        font_btn.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.btn_download.setFont(font_btn)
        self.btn_download.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_download.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        
        icon_download = QtGui.QIcon()
        icon_download.addPixmap(QtGui.QPixmap("app/gui/icons/downloading.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.btn_download.setIconSize(QtCore.QSize(15, 15))
        self.btn_download.setIcon(icon_download)
        self.btn_download.setFixedSize(150, 36)

        self.btn_download.setStyleSheet("""
            QPushButton {
                background-color: rgba(33, 150, 243, 0.15);
                color: #64B5F6;
                border: 1px solid rgba(33, 150, 243, 0.3);
                border-radius: 8px;
                padding: 0px 15px;
            }
            QPushButton:hover {
                background-color: rgba(33, 150, 243, 0.35);
                border: 1px solid rgba(33, 150, 243, 0.6);
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: rgba(33, 150, 243, 0.1);
            }
        """)

        try:
            self.btn_download.clicked.disconnect()
        except TypeError:
            pass

        self.btn_download.clicked.connect(lambda: download_model_method(model_id))

        self.btn_hf = QPushButton("🤗")
        self.btn_hf.setToolTip("Open model page on Hugging Face")
        font = QtGui.QFont()
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.btn_hf.setFont(font)
        self.btn_hf.setFixedSize(36, 36)
        self.btn_hf.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_hf.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_hf.setStyleSheet("""
            QToolTip {
                background-color: rgba(25, 25, 30, 0.95); 
                color: #E0E0E0; 
                border: 1px solid rgba(255, 255, 255, 0.15); 
                border-radius: 6px; 
                padding: 6px 10px; font-size: 13px; 
                font-family: 'Inter Tight SemiBold';
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                font-size: 15px;
            }
            QPushButton:hover {
                background-color: rgba(255, 210, 30, 0.15);
                border: 1px solid rgba(255, 210, 30, 0.4);
            }
            QPushButton:pressed {
                background-color: rgba(255, 210, 30, 0.08);
            }
        """)
        self.btn_hf.clicked.connect(lambda _, mid=model_id: QDesktopServices.openUrl(QUrl(f"https://huggingface.co/{mid}")))

        card_layout.addWidget(self.btn_hf, alignment=QtCore.Qt.AlignmentFlag.AlignVCenter)
        card_layout.addWidget(self.btn_download, alignment=QtCore.Qt.AlignmentFlag.AlignVCenter)

        main_layout.addWidget(self.glass_card)
        self.setLayout(main_layout)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mousePressEvent = self.on_click

    def enterEvent(self, event):
        self.glass_card.setStyleSheet(self.glass_style_hover)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.glass_card.setStyleSheet(self.glass_style_normal)
        super().leaveEvent(event)

    def on_click(self, event):
        self.show_model_info_method(self.model_id)

class ModelPopular(QThread):
    """
    A thread-based class for fetching the most downloaded GGUF models from Hugging Face Hub.
    
    This class searches for trending GGUF models and emits progress updates as it processes them.
    Once completed, it returns a list of model IDs sorted by download count in descending order.
    
    Signals:
        progress (str, str, int): Emits model_id, author, downloads for each processed model.
        finished (list): Emits the final list of model IDs after processing completes.
        error (str): Emits an error message if something goes wrong during execution.
    """
    progress = pyqtSignal(str, str, int)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.api = HfApi()

    def run(self):
        try:
            models = list(self.api.list_models(
                search="gguf",
                limit=100,
                sort="downloads",
                direction=-1
            ))

            relevant_models = []

            for model in models:
                model_id = model.id
                info = self.api.model_info(model_id)

                author = info.author or "Unknown"
                downloads = info.downloads or 0

                relevant_models.append(model_id)

                self.progress.emit(model_id, author, downloads)

            self.finished.emit(relevant_models)

        except Exception as e:
            self.error.emit(str(e))

class ModelItemWidget(QWidget):
    def __init__(self, model_id, author, downloads, show_model_info_method, 
                 download_model_method, parent=None, download_button_translation=" Download model", 
                 author_label_translation="Author - ", downloads_label_translation="Downloads - "):
        super().__init__(parent)
        
        self.model_id = model_id
        self.show_model_info_method = show_model_info_method

        self.setFixedHeight(85)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 2, 5, 2) 
        main_layout.setSpacing(0)

        self.glass_card = QtWidgets.QFrame(self)
        self.glass_style_normal = """
            QFrame {
                background-color: rgba(25, 25, 30, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
            }
        """
        self.glass_style_hover = """
            QFrame {
                background-color: rgba(35, 35, 45, 0.65);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 16px;
            }
        """
        self.glass_card.setStyleSheet(self.glass_style_normal)

        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QtGui.QColor(0, 0, 0, 80))
        shadow.setOffset(0, 5)
        self.glass_card.setGraphicsEffect(shadow)

        card_layout = QHBoxLayout(self.glass_card)
        card_layout.setContentsMargins(12, 10, 12, 10) 
        card_layout.setSpacing(15)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)

        model_name = model_id.split("/")[-1]
        self.name_label = QLabel(model_name)
        font_name = QtGui.QFont("Inter Tight SemiBold", 12, QtGui.QFont.Weight.Bold)
        font_name.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.name_label.setFont(font_name)
        self.name_label.setStyleSheet("color: rgba(255, 255, 255, 0.95); background: transparent; border: none;")
        info_layout.addWidget(self.name_label)

        meta_row_layout = QHBoxLayout()
        meta_row_layout.setSpacing(8)

        badge_style = """
            QLabel {
                background-color: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
                font-family: 'Inter Tight Medium';
            }
        """

        self.author_label = QLabel(f"👤 {author_label_translation} {author}")
        font = QtGui.QFont()
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.author_label.setFont(font)
        self.author_label.setFixedHeight(20)
        self.author_label.setStyleSheet(badge_style)
        meta_row_layout.addWidget(self.author_label)

        self.downloads_label = QLabel(f"⬇️ {downloads_label_translation} {downloads}")
        font = QtGui.QFont()
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.downloads_label.setFont(font)
        self.downloads_label.setFixedHeight(20)
        self.downloads_label.setStyleSheet(badge_style)
        meta_row_layout.addWidget(self.downloads_label)
        meta_row_layout.addStretch()

        info_layout.addLayout(meta_row_layout)
        card_layout.addLayout(info_layout, stretch=1)

        self.btn_download = QPushButton(download_button_translation)
        font_btn = QtGui.QFont("Inter Tight SemiBold", 9)
        font_btn.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.btn_download.setFont(font_btn)
        self.btn_download.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_download.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        
        icon_download = QtGui.QIcon()
        icon_download.addPixmap(QtGui.QPixmap("app/gui/icons/downloading.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.btn_download.setIconSize(QtCore.QSize(15, 15))
        self.btn_download.setIcon(icon_download)
        self.btn_download.setFixedSize(150, 36)

        self.btn_download.setStyleSheet("""
            QPushButton {
                background-color: rgba(33, 150, 243, 0.15);
                color: #64B5F6;
                border: 1px solid rgba(33, 150, 243, 0.3);
                border-radius: 8px;
                padding: 0px 15px;
            }
            QPushButton:hover {
                background-color: rgba(33, 150, 243, 0.35);
                border: 1px solid rgba(33, 150, 243, 0.6);
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: rgba(33, 150, 243, 0.1);
            }
        """)

        try:
            self.btn_download.clicked.disconnect()
        except TypeError:
            pass

        self.btn_download.clicked.connect(lambda: download_model_method(model_id))

        self.btn_hf = QPushButton("🤗")
        self.btn_hf.setToolTip("Open model page on Hugging Face")
        font = QtGui.QFont()
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.btn_hf.setFont(font)
        self.btn_hf.setFixedSize(36, 36)
        self.btn_hf.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_hf.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_hf.setStyleSheet("""
            QToolTip {
                background-color: rgba(25, 25, 30, 0.95); 
                color: #E0E0E0; 
                border: 1px solid rgba(255, 255, 255, 0.15); 
                border-radius: 6px; 
                padding: 6px 10px; font-size: 13px; 
                font-family: 'Inter Tight SemiBold';
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                font-size: 15px;
            }
            QPushButton:hover {
                background-color: rgba(255, 210, 30, 0.15);
                border: 1px solid rgba(255, 210, 30, 0.4);
            }
            QPushButton:pressed {
                background-color: rgba(255, 210, 30, 0.08);
            }
        """)
        self.btn_hf.clicked.connect(lambda _, mid=model_id: QDesktopServices.openUrl(QUrl(f"https://huggingface.co/{mid}")))

        card_layout.addWidget(self.btn_hf, alignment=QtCore.Qt.AlignmentFlag.AlignVCenter)
        card_layout.addWidget(self.btn_download, alignment=QtCore.Qt.AlignmentFlag.AlignVCenter)

        main_layout.addWidget(self.glass_card)
        self.setLayout(main_layout)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mousePressEvent = self.on_click
    
    def enterEvent(self, event):
        self.glass_card.setStyleSheet(self.glass_style_hover)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.glass_card.setStyleSheet(self.glass_style_normal)
        super().leaveEvent(event)

    def on_click(self, event):
        self.show_model_info_method(self.model_id)

    def set_data(self, author="", downloads=0):
        self.author_label.setText(f"👤 Author: {author}")
        self.downloads_label.setText(f"⬇️ Downloads: {downloads}")

class ModelInformation(QThread):
    """
    A thread-based class for fetching detailed information about a specific model from Hugging Face Hub.
    
    This class retrieves metadata and description of a given model. If the description is not available
    in the model card, it attempts to extract it from the README.md file.

    Signals:
        finished (dict): Emits a dictionary with detailed model information.
        error (str): Emits an error message if something goes wrong during execution.
    """
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, model_id):
        super().__init__()
        self.model_id = model_id
        self.api = HfApi()

    def run(self):
        try:
            info = self.api.model_info(self.model_id)
            card_data = info.card_data.to_dict() if hasattr(info.card_data, "to_dict") else info.card_data or {}
            description = card_data.get("description", None)

            if not description:
                try:
                    readme_path = hf_hub_download(repo_id=self.model_id, filename="README.md")
                    with open(readme_path, "r", encoding="utf-8") as f:
                        readme_text = f.read()
                    description = self.extract_description_from_readme(readme_text)
                except:
                    description = "Description not found"

            model_data = {
                "id": info.id,
                "tags": ", ".join(info.tags) if info.tags else "No tags",
                "pipeline_tag": info.pipeline_tag or "Undefined",
                "author": info.author or "Undefined",
                "last_modified": str(info.last_modified) if info.last_modified else "Undefined",
                "downloads": info.downloads or 0,
                "description": description,
                "license": card_data.get("license", "Undefined"),
                "library_name": info.library_name or "Undefined",
                "inference": info.inference or "Undefined",
                "likes": info.likes or 0,
                "trending_score": info.trending_score or 0,
            }
            self.finished.emit(model_data)
        except Exception as e:
            self.error.emit(str(e))
    
    def extract_description_from_readme(self, text):
        blocks = text.strip().split('\n\n')
        paragraphs = []

        for block in blocks:
            stripped_block = block.strip()
            if not stripped_block:
                continue

            if stripped_block.startswith('#'):
                continue

            paragraphs.append(stripped_block)

        return "<br><br>".join(paragraphs)

class ModelRepoFiles(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, model_id):
        super().__init__()
        self.model_id = model_id
        self.api = HfApi()

    def run(self):
        try:
            repo_files = [
                item for item in self.api.list_repo_tree(
                    repo_id=self.model_id,
                    recursive=True,
                    expand=False,
                    repo_type="model"
                )
            ]
            gguf_files = [
                (file.path, file.size) for file in repo_files if file.rfilename.endswith(".gguf")
            ]
            self.finished.emit(gguf_files)
        except Exception as e:
            self.error.emit(str(e))

class FileSelectorDialog(QDialog):
    def __init__(self, files_with_size, translations, model_id):
        super().__init__()
        self.translations = translations if translations else {}
        self.setWindowTitle(self.translations.get("download_model_title", "Download Model"))
        
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("app/gui/icons/logotype.ico"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.setWindowIcon(icon)
        self.setMinimumSize(950, 650)
        self.selected_file = None
        self.active_downloaders = [] 
        
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0F0F13, stop:1 #1A1A24);
                color: #E2E8F0;
                font-family: 'Segoe UI Variable', 'Segoe UI', 'Inter', sans-serif;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        header_layout = QVBoxLayout()
        header_layout.setSpacing(5)
        
        title_label = QLabel(self.translations.get("select_quant_title", "Select Quantization Level"))
        font_title = QtGui.QFont("Inter Tight SemiBold", 16, QtGui.QFont.Weight.Bold)
        font_title.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        title_label.setFont(font_title)
        title_label.setStyleSheet("color: #FFFFFF;")
        
        avail_text = self.translations.get("available_files_text", "Available files for repository:")
        rec_text = self.translations.get("quant_recommendation_text", "We recommend downloading files with 'Q4_K_M' or 'Q5_K_M' for the best balance of speed and quality.")
        
        subtitle_label = QLabel(f"{avail_text} <span style='color: #60A5FA;'>{model_id}</span><br>"
                                f"<span style='color: #64748B;'>{rec_text}</span>")
        
        font_sub = QtGui.QFont("Inter Tight Medium", 10)
        font_sub.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        subtitle_label.setFont(font_sub)
        subtitle_label.setTextFormat(Qt.TextFormat.RichText)
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        layout.addLayout(header_layout)
        
        self.file_list = QListWidget()
        self.file_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.file_list.setSpacing(12)
        self.file_list.setStyleSheet("""
            QListWidget { background: transparent; outline: 0px; border: none; }
            QListWidget::item { background: transparent; border: none; }
            QScrollBar:vertical { background: transparent; width: 8px; margin: 0px; }
            QScrollBar::handle:vertical { background: rgba(255, 255, 255, 0.15); border-radius: 4px; min-height: 40px; }
            QScrollBar::handle:vertical:hover { background: rgba(255, 255, 255, 0.3); }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)
        
        for filename, size_bytes in files_with_size:
            size_str = self.human_readable_size(size_bytes)
            widget = FileSelectorItemWidget(
                parent=self.file_list, 
                filename=filename, 
                model_size=size_str, 
                translations=self.translations, 
                model_id=model_id
            )
            item = QListWidgetItem()
            item.setSizeHint(QtCore.QSize(0, 100))
            item.setData(Qt.ItemDataRole.UserRole, filename)
            
            self.file_list.addItem(item)
            self.file_list.setItemWidget(item, widget)

        self.file_list.itemDoubleClicked.connect(self.accept_selection)
        layout.addWidget(self.file_list)

    def accept_selection(self):
        selected_items = self.file_list.selectedItems()
        if selected_items:
            self.selected_file = selected_items[0].data(Qt.ItemDataRole.UserRole)
            self.accept()

    def human_readable_size(self, size_bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} TB"

    def closeEvent(self, event):
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            widget = self.file_list.itemWidget(item)
            if isinstance(widget, FileSelectorItemWidget):
                if hasattr(widget, 'downloader_thread') and widget.downloader_thread and widget.downloader_thread.isRunning():
                    widget.downloader_thread.cancel()
                    widget.downloader_thread.wait(2000)
        super().closeEvent(event)


class FileSelectorItemWidget(QtWidgets.QFrame):
    def __init__(self, parent=None, filename="Unknown", model_size="0 MB", translations=None, model_id="None"):
        super().__init__(parent)
        self.model_id = model_id
        self.filename = filename
        self.translations = translations if translations else {}
        self.downloader_thread = None

        self.setObjectName("ModelCard")
        
        self.style_normal = """
            QFrame#ModelCard {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 12px;
            }
        """
        self.style_hover = """
            QFrame#ModelCard {
                background-color: rgba(96, 165, 250, 0.08);
                border: 1px solid rgba(96, 165, 250, 0.3);
                border-radius: 12px;
            }
        """
        self.setStyleSheet(self.style_normal)

        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QtGui.QColor(0, 0, 0, 60))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 15, 20, 15)
        main_layout.setSpacing(20)

        left_layout = QVBoxLayout()
        left_layout.setSpacing(8)

        self.name_label = QLabel(filename)
        font_name = QtGui.QFont("Inter Tight SemiBold", 13, QtGui.QFont.Weight.Bold)
        font_name.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.name_label.setFont(font_name)
        self.name_label.setStyleSheet("color: #F8FAFC; background: transparent; border: none;")
        left_layout.addWidget(self.name_label)

        self.stacked_widget = QtWidgets.QStackedWidget()
        self.stacked_widget.setFixedHeight(35)
        self.stacked_widget.setStyleSheet("background: transparent;")

        page_badges = QWidget()
        badges_layout = QHBoxLayout(page_badges)
        badges_layout.setContentsMargins(0, 0, 0, 0)
        badges_layout.setSpacing(10)
        
        self.size_badge = QLabel(f"💾 {model_size}")
        self.size_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        font_badge = QtGui.QFont("Inter Tight Medium", 9)
        font_badge.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.size_badge.setFont(font_badge)
        self.size_badge.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 0.05); color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px;
                padding: 4px 10px;
            }
        """)
        
        format_badge = QLabel("⚙️ GGUF")
        format_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        format_badge.setFont(font_badge)
        format_badge.setStyleSheet("""
            QLabel {
                background-color: rgba(59, 130, 246, 0.1); color: #93C5FD;
                border: 1px solid rgba(59, 130, 246, 0.2); border-radius: 6px;
                padding: 4px 10px;
            }
        """)

        self.status_ready = QLabel(self.translations.get("status_ready_download", "Ready to download"))
        self.status_ready.setFont(font_badge)
        self.status_ready.setStyleSheet("color: #64748B;")

        badges_layout.addWidget(self.size_badge)
        badges_layout.addWidget(format_badge)
        badges_layout.addWidget(self.status_ready)
        badges_layout.addStretch()
        self.stacked_widget.addWidget(page_badges)

        page_progress = QWidget()
        progress_layout = QVBoxLayout(page_progress)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(4)
        
        self.status_label = QLabel(self.translations.get("status_init_download", "Initializing download..."))
        font_status = QtGui.QFont("Inter Tight Medium", 9)
        font_status.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.status_label.setFont(font_status)
        self.status_label.setStyleSheet("color: #93C5FD; font-weight: bold;")
        progress_layout.addWidget(self.status_label)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(0, 0, 0, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3B82F6, stop:1 #8B5CF6);
                border-radius: 2px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        self.stacked_widget.addWidget(page_progress)

        left_layout.addWidget(self.stacked_widget)
        main_layout.addLayout(left_layout, stretch=1)

        download_text = self.translations.get("btn_download_model", " Download")
        self.btn_download = QPushButton(download_text)
        
        font_btn = QtGui.QFont("Inter Tight SemiBold", 10)
        font_btn.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.btn_download.setFont(font_btn)
        
        self.icon_download = QtGui.QIcon()
        self.icon_download.addPixmap(QtGui.QPixmap("app/gui/icons/downloading.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.btn_download.setIcon(self.icon_download)
        self.btn_download.setIconSize(QtCore.QSize(18, 18))
        self.btn_download.setFixedSize(140, 42)
        self.btn_download.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_download.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.btn_style_normal = """
            QPushButton {
                background-color: rgba(59, 130, 246, 0.15); color: #93C5FD;
                border: 1px solid rgba(59, 130, 246, 0.4); border-radius: 8px;
            }
            QPushButton:hover {
                background-color: rgba(59, 130, 246, 0.3); border: 1px solid rgba(59, 130, 246, 0.6); color: #FFFFFF;
            }
            QPushButton:pressed { background-color: rgba(59, 130, 246, 0.1); }
        """
        self.btn_style_stop = """
            QPushButton {
                background-color: rgba(239, 68, 68, 0.15); color: #FCA5A5;
                border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 8px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.3); border: 1px solid rgba(239, 68, 68, 0.6); color: #FFFFFF;
            }
        """
        self.btn_style_success = """
            QPushButton {
                background-color: rgba(16, 185, 129, 0.15); color: #6EE7B7;
                border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 8px;
            }
        """
        self.btn_style_error = """
            QPushButton {
                background-color: rgba(244, 67, 54, 0.15); color: #E57373;
                border: 1px solid rgba(244, 67, 54, 0.3); border-radius: 8px;
            }
        """
        
        self.btn_download.setStyleSheet(self.btn_style_normal)
        self.btn_download.clicked.connect(self.start_download)
        main_layout.addWidget(self.btn_download, alignment=Qt.AlignmentFlag.AlignVCenter)

    def enterEvent(self, event):
        if self.btn_download.isEnabled():
            self.setStyleSheet(self.style_hover)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet(self.style_normal)
        super().leaveEvent(event)

    def start_download(self):
        stop_text = self.translations.get("btn_stop_download", "🛑 Stop")
        self.btn_download.setText(stop_text)
        self.btn_download.setIcon(QtGui.QIcon()) 
        self.btn_download.setStyleSheet(self.btn_style_stop)
        
        try: self.btn_download.clicked.disconnect()
        except TypeError: pass
        self.btn_download.clicked.connect(self.cancel_download)
        
        self.stacked_widget.setCurrentIndex(1)
        self.progress_bar.setValue(0)

        self.downloader_thread = FileDownloader(self.model_id, self.filename, self.translations)
        self.downloader_thread.progress.connect(self.on_download_progress)
        self.downloader_thread.finished.connect(self.on_download_finished)
        self.downloader_thread.error.connect(self.on_download_error)
        self.downloader_thread.cancelled.connect(self.on_download_cancelled)
        self.downloader_thread.start()

    def cancel_download(self):
        self.btn_download.setEnabled(False)
        self.btn_download.setText(self.translations.get("btn_stopping", " Stopping..."))
        self.status_label.setText(self.translations.get("status_cancelling", "Cancelling download and cleaning up..."))
        if self.downloader_thread:
            self.downloader_thread.cancel()

    def on_download_cancelled(self):
        self.btn_download.setEnabled(True)
        self.btn_download.setText(self.translations.get("btn_download_model", " Download"))
        self.btn_download.setIcon(self.icon_download)
        self.btn_download.setStyleSheet(self.btn_style_normal)
        
        try: self.btn_download.clicked.disconnect()
        except TypeError: pass
        self.btn_download.clicked.connect(self.start_download)
        
        self.stacked_widget.setCurrentIndex(0) 

    def on_download_progress(self, percent, text_status):
        self.progress_bar.setValue(percent)
        self.status_label.setText(text_status)

    def on_download_finished(self, path):
        self.btn_download.setEnabled(False)
        self.btn_download.setText(self.translations.get("btn_downloaded", " Downloaded ✓"))
        self.btn_download.setStyleSheet(self.btn_style_success)
        
        try: self.btn_download.clicked.disconnect()
        except TypeError: pass
        
        self.progress_bar.setValue(100)
        self.status_label.setText(self.translations.get("status_download_complete", "Download Complete!"))
        self.status_label.setStyleSheet("color: #4ADE80; font-size: 12px; font-weight: bold;")

    def on_download_error(self, error_msg):
        self.btn_download.setEnabled(True)
        self.btn_download.setText(self.translations.get("btn_try_again", " Try Again"))
        self.btn_download.setIcon(self.icon_download)
        self.btn_download.setStyleSheet(self.btn_style_error)
        
        try: self.btn_download.clicked.disconnect()
        except TypeError: pass
        self.btn_download.clicked.connect(self.start_download)
        
        self.stacked_widget.setCurrentIndex(0)
        
        error_template = self.translations.get("error_download_failed", "Failed to download {filename}:\n\n{error_msg}")
        error_text = error_template.replace("{filename}", self.filename).replace("{error_msg}", error_msg)
        
        parent_win = self.window() if hasattr(self, "window") else self

        sow_toast(
            parent=parent_win,
            title=self.translations.get("error_title", "Download Error"),
            text=error_text,
            msg_type="error"
        )


class FileDownloader(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, model_id, filename, translations):
        super().__init__()
        self.model_id = model_id
        self.filename = filename
        self.translations = translations
        self.save_dir = "assets/local_llm"
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            os.makedirs(self.save_dir, exist_ok=True)
            local_path = os.path.join(self.save_dir, self.filename)

            url = f"https://huggingface.co/{self.model_id}/resolve/main/{self.filename}"
            
            with requests.get(url, stream=True, allow_redirects=True, timeout=10) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                downloaded = 0
                
                start_time = time.time()
                last_update_time = start_time

                with open(local_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024*128):
                        if self._is_cancelled:
                            break
                            
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            current_time = time.time()
                            if current_time - last_update_time > 0.1:
                                if total_size:
                                    percent = int((downloaded / total_size) * 100)
                                    elapsed_time = current_time - start_time
                                    speed_bps = downloaded / elapsed_time if elapsed_time > 0 else 0
                                    remaining_bytes = total_size - downloaded
                                    eta_seconds = remaining_bytes / speed_bps if speed_bps > 0 else 0
                                    
                                    down_str = self.format_size(downloaded)
                                    total_str = self.format_size(total_size)
                                    speed_str = f"{self.format_size(speed_bps)}/s"
                                    
                                    tr_h = self.translations.get("time_h", "h")
                                    tr_m = self.translations.get("time_m", "m")
                                    tr_s = self.translations.get("time_s", "s")
                                    tr_left = self.translations.get("time_left", "left")

                                    if eta_seconds > 3600:
                                        eta_str = f"{int(eta_seconds // 3600)}{tr_h} {int((eta_seconds % 3600) // 60)}{tr_m} {tr_left}"
                                    elif eta_seconds > 60:
                                        eta_str = f"{int(eta_seconds // 60)}{tr_m} {int(eta_seconds % 60)}{tr_s} {tr_left}"
                                    else:
                                        eta_str = f"{int(eta_seconds)}{tr_s} {tr_left}"

                                    text_status = f"{down_str} / {total_str}  •  {speed_str}  •  {eta_str}"
                                    self.progress.emit(percent, text_status)
                                
                                last_update_time = current_time
            
            if self._is_cancelled:
                if os.path.exists(local_path):
                    os.remove(local_path)
                self.cancelled.emit()
                return
                                
            self.finished.emit(local_path)
            
        except requests.exceptions.RequestException as e:
            if not self._is_cancelled:
                self.error.emit(self.translations.get("network_error", "Network error: ") + str(e))
        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(self.translations.get("system_error", "System error: ") + str(e))

    def format_size(self, size_bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} TB"
