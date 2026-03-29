import os
import logging
import urllib.request
import ssl
import json

from datetime import datetime, timedelta

from PyQt6 import QtCore, QtWidgets, QtGui
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QListWidget, QLabel, QDialog, 
    QVBoxLayout as QVBox, QListWidgetItem
)

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
            
            if not curated_data or "models" not in curated_data:
                fallback_models = self.get_fallback_models()
                for model in fallback_models:
                    model_id = model.get("hf_id", "")
                    author = model.get("author", "Unknown")
                    downloads = model.get("downloads", 0)
                    compatibility_text, is_compatible = self.check_compatibility(model)
                    self.progress.emit(model_id, author, downloads, compatibility_text, is_compatible)
                self.finished.emit([m["hf_id"] for m in fallback_models])
                return
            
            models = curated_data["models"]
            model_ids = []

            for model in models:
                model_id = model.get("hf_id", "")
                author = model.get("author", "Unknown")
                downloads = model.get("downloads", 0)
                
                compatibility_text, is_compatible = self.check_compatibility(model)
                
                model_ids.append(model_id)
                self.progress.emit(model_id, author, downloads, compatibility_text, is_compatible)

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
        
        user_ram = self.available_ram_gb
        
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
            return f"✅ Will run on CPU", True
    
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

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 5, 0, 5)

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
        card_layout.setContentsMargins(20, 15, 20, 15)
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
        self.author_label.setFixedHeight(20)
        self.author_label.setStyleSheet(badge_style)
        meta_row_layout.addWidget(self.author_label)

        self.downloads_label = QLabel(f"⬇️ {downloads_label_translation} {downloads}")
        self.downloads_label.setFixedHeight(20)
        self.downloads_label.setStyleSheet(badge_style)
        meta_row_layout.addWidget(self.downloads_label)

        self.compatibility_label = QLabel(f"{compatibility_label_translation} {compatibility_text}")
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

        if not is_compatible and "❌" in compatibility_text:
            self.btn_download.setEnabled(False)
            self.btn_download.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.02);
                    color: rgba(255, 255, 255, 0.2);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    border-radius: 8px;
                }
            """)
        else:
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

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 5, 0, 5)

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
        card_layout.setContentsMargins(20, 15, 20, 15)
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
        self.author_label.setFixedHeight(20)
        self.author_label.setStyleSheet(badge_style)
        meta_row_layout.addWidget(self.author_label)

        self.downloads_label = QLabel(f"⬇️ {downloads_label_translation} {downloads}")
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
    def __init__(self, files_with_size, download_button_translation, model_id):
        super().__init__()
        self.setWindowTitle("File Selector")
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("app/gui/icons/logotype.ico"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.setWindowIcon(icon)
        self.setMinimumSize(1000, 580)
        self.selected_file = None
        
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e24;
                color: #e0e0e0;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        
        self.file_list = QListWidget()
        self.file_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.file_list.setStyleSheet("""
            QListWidget {
                background: transparent;
                outline: 0px;
                border: none;
            }
            QListWidget::item {
                background: transparent;
                border: none;
                padding: 5px 10px;
            }
            QListWidget::item:selected {
                background: transparent;
                border: none;
            }
            QListWidget::item:hover {
                background: transparent;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.15);
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.25);
            }
            QScrollBar::handle:vertical:pressed {
                background: rgba(255, 255, 255, 0.15);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        for filename, size_bytes in files_with_size:
            size_str = self.human_readable_size(size_bytes)
            item = QListWidgetItem()
            widget = FileSelectorItemWidget(
                parent=self.file_list, 
                filename=filename, 
                model_size=size_str, 
                download_button_translation=download_button_translation, 
                model_id=model_id
            )
            item.setSizeHint(widget.sizeHint())
            item.setData(Qt.ItemDataRole.UserRole, filename)
            self.file_list.addItem(item)
            self.file_list.setItemWidget(item, widget)

        self.file_list.itemDoubleClicked.connect(self.accept_selection)
        layout.addWidget(self.file_list)

        self.setLayout(layout)

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

class FileSelectorItemWidget(QWidget):
    def __init__(self, parent=None, filename="Unknown", model_size=0, download_button_translation=" Download", model_id="None"):
        super().__init__(parent)
        self.model_id = model_id
        self.filename = filename

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 5, 0, 5)

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
        card_layout.setContentsMargins(20, 15, 20, 15)
        card_layout.setSpacing(15)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)

        self.name_label = QLabel(filename)
        font_name = QtGui.QFont("Inter Tight SemiBold", 11, QtGui.QFont.Weight.Bold)
        font_name.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.name_label.setFont(font_name)
        self.name_label.setStyleSheet("color: rgba(255, 255, 255, 0.95); background: transparent; border: none;")
        info_layout.addWidget(self.name_label)

        meta_row_layout = QHBoxLayout()
        meta_row_layout.setSpacing(8)

        self.size_badge = QLabel(f"💾 {model_size}")
        self.size_badge.setFixedHeight(20)
        self.size_badge.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
                font-family: 'Inter Tight Medium';
            }
        """)
        meta_row_layout.addWidget(self.size_badge)
        meta_row_layout.addStretch()

        info_layout.addLayout(meta_row_layout)
        card_layout.addLayout(info_layout, stretch=1)

        self.btn_download = QPushButton(download_button_translation)
        font_btn = QtGui.QFont("Inter Tight SemiBold", 9)
        font_btn.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.btn_download.setFont(font_btn)
        icon_download = QtGui.QIcon()
        icon_download.addPixmap(QtGui.QPixmap("app/gui/icons/downloading.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.btn_download.setIconSize(QtCore.QSize(15, 15))
        self.btn_download.setIcon(icon_download)
        self.btn_download.setFixedSize(160, 36)
        self.btn_download.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_download.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))

        self.btn_style_normal = """
            QPushButton {
                background-color: rgba(33, 150, 243, 0.15);
                color: #64B5F6;
                border: 1px solid rgba(33, 150, 243, 0.3);
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: rgba(33, 150, 243, 0.35);
                border: 1px solid rgba(33, 150, 243, 0.6);
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: rgba(33, 150, 243, 0.1);
            }
        """
        self.btn_style_downloading = """
            QPushButton {
                background-color: rgba(255, 152, 0, 0.15);
                color: #FFB74D;
                border: 1px solid rgba(255, 152, 0, 0.3);
                border-radius: 8px;
            }
        """
        self.btn_style_success = """
            QPushButton {
                background-color: rgba(76, 175, 80, 0.15);
                color: #81C784;
                border: 1px solid rgba(76, 175, 80, 0.3);
                border-radius: 8px;
            }
        """
        self.btn_style_error = """
            QPushButton {
                background-color: rgba(244, 67, 54, 0.15);
                color: #E57373;
                border: 1px solid rgba(244, 67, 54, 0.3);
                border-radius: 8px;
            }
        """

        self.btn_download.setStyleSheet(self.btn_style_normal)

        try:
            self.btn_download.clicked.disconnect()
        except TypeError:
            pass

        self.btn_download.clicked.connect(self.download_model_method)

        card_layout.addWidget(self.btn_download, alignment=Qt.AlignmentFlag.AlignVCenter)

        main_layout.addWidget(self.glass_card)
        self.setLayout(main_layout)
    
    def enterEvent(self, event):
        self.glass_card.setStyleSheet(self.glass_style_hover)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.glass_card.setStyleSheet(self.glass_style_normal)
        super().leaveEvent(event)

    def download_model_method(self):
        self.btn_download.setEnabled(False)
        self.btn_download.setText(" Downloading...")
        self.btn_download.setStyleSheet(self.btn_style_downloading)

        self.downloader_thread = FileDownloader(self.model_id, self.filename)
        self.downloader_thread.finished.connect(self.on_download_finished)
        self.downloader_thread.error.connect(self.on_download_error)
        self.downloader_thread.start()

    def on_download_finished(self, path):
        self.btn_download.setText(" Downloaded ✓")
        self.btn_download.setStyleSheet(self.btn_style_success)

    def on_download_error(self, error_msg):
        self.btn_download.setText(" Error")
        self.btn_download.setStyleSheet(self.btn_style_error)
        
        error_box = QtWidgets.QMessageBox()
        error_box.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        error_box.setWindowTitle("Download Error")
        error_box.setText(error_msg)
        error_box.setStyleSheet("""
            QMessageBox {
                background-color: #1e1e24;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 5px 15px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
        """)
        error_box.setIcon(QtWidgets.QMessageBox.Icon.Critical)
        error_box.exec()

class FileDownloader(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, model_id, filename):
        super().__init__()
        self.model_id = model_id
        self.filename = filename
        self.save_dir = "assets/local_llm"

    def run(self):
        try:
            os.makedirs(self.save_dir, exist_ok=True)

            local_path = hf_hub_download(
                repo_id=self.model_id,
                filename=self.filename,
                revision="main",
                local_dir=self.save_dir,
            )

            self.finished.emit(local_path)
        except Exception as e:
            self.error.emit(str(e))
