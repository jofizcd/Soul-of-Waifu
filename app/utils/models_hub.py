import os
import logging

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
    A thread-based class for recommending GGUF models based on available RAM and quantization type.
    
    This class filters models from Hugging Face Hub that match the quantization criteria
    and fit within the provided RAM limit. It emits progress updates during filtering
    and returns a list of suitable models at the end.

    Signals:
        progress (str, str, int): Emits model_id, author, downloads as each valid model is found.
        finished (list): Emits the final list of suitable model IDs.
        error (str): Emits an error message if something goes wrong.
    """
    progress = pyqtSignal(str, str, int)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, available_ram_gb=8):
        super().__init__()
        self.api = HfApi()
        self.available_ram_bytes = available_ram_gb * 1024 * 1024 * 1024
        self.quantization_type = "Q4" or "q4" or "Q4_K_S"

    def run(self):
        try:
            models = list(self.api.list_models(
                search="gguf",
                limit=100,
                sort="trending_score",
                direction=-1
            ))

            relevant_files = []
            suitable_model_ids = []

            for model in models:
                model_id = model.id
                info = self.api.model_info(model_id)

                author = info.author or "Unknown"
                downloads = info.downloads or 0

                repo_files = [
                    item for item in self.api.list_repo_tree(
                        repo_id=model_id,
                        recursive=True,
                        expand=False,
                        repo_type="model"
                    )
                ]

                for f in repo_files:
                    if hasattr(f, "rfilename") and f.rfilename.endswith(".gguf"):
                        if self.quantization_type.lower() in f.rfilename.lower():
                            relevant_files.append((f.rfilename, f.size))

                if not relevant_files:
                    continue

                smallest_file = min(relevant_files, key=lambda x: x[1])

                if smallest_file[1] <= self.available_ram_bytes:
                    suitable_model_ids.append(model_id)
                    self.progress.emit(model_id, author, downloads)

            self.finished.emit(suitable_model_ids)

        except Exception as e:
            self.error.emit(str(e))

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

        self.setStyleSheet("border: 1px solid rgb(50, 50, 55);")
        layout = QHBoxLayout()
        layout.setContentsMargins(50, 20, 50, 20)
        layout.setSpacing(10)

        info_layout = QVBoxLayout()

        model_name = model_id.split("/")[-1]
        self.name_label = QLabel(f"<b>{model_name}</b>")
        self.name_label.setMinimumHeight(20)
        self.name_label.setStyleSheet("color: rgb(227, 227, 227); font-weight: bold; font-size: 14px; background: transparent; border: none;")
        self.author_label = QLabel(f"{author_label_translation} {author}")
        self.author_label.setMinimumHeight(20)
        self.author_label.setStyleSheet("color: rgb(210, 210, 210); font-size: 12px; background: transparent; border: none;")
        self.downloads_label = QLabel(f"{downloads_label_translation} {downloads}")
        self.downloads_label.setMinimumHeight(20)
        self.downloads_label.setStyleSheet("color: rgb(210, 210, 210); font-size: 12px; background: transparent; border: none;")

        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.name_label.setFont(font)
        self.author_label.setFont(font)
        self.downloads_label.setFont(font)

        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.author_label)
        info_layout.addWidget(self.downloads_label)

        btn_layout = QVBoxLayout()

        self.btn_download = QPushButton(download_button_translation)
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(9)
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.btn_download.setFont(font)
        self.btn_download.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        icon_download = QtGui.QIcon()
        icon_download.addPixmap(QtGui.QPixmap("app/gui/icons/downloading.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.btn_download.setIconSize(QtCore.QSize(15, 15))
        self.btn_download.setIcon(icon_download)
        self.btn_download.setFixedSize(160, 35)
        self.btn_download.setStyleSheet("""
            QPushButton {
                background-color: #2E2E2E;
                color: rgb(227, 227, 227);
                border-radius: 8px;
                font-size: 12px;
                border: 1px solid #444444;
            }

            QPushButton:hover {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                stop: 0 #3A3A3A, stop: 1 #2F2F2F);
                border: 1px solid #666666;
            }

            QPushButton:pressed {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                stop: 0 #2A2A2A, stop: 1 #444444);
                border: 1px solid #888888;
            }

            QPushButton:disabled {
                background-color: #222222;
                color: #777777;
                border: 1px solid #333333;
            }
        """)

        try:
            self.btn_download.clicked.disconnect()
        except TypeError:
            pass

        self.btn_download.clicked.connect(lambda: download_model_method(model_id))

        btn_layout.addWidget(self.btn_download)

        layout.addLayout(info_layout)
        layout.addLayout(btn_layout)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.setLayout(layout)

        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.mousePressEvent = self.on_click
    
    def on_click(self, event):
        self.show_model_info_method(self.model_id)

    def set_data(self, author="", downloads=0):
        self.author_label.setText(f"Author: {author}")
        self.downloads_label.setText(f"Downloads: {downloads}")

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
                background-color: #1e1e1e;
                color: #dcdcdc;
            }
            QLabel {
                font-size: 14px;
                margin-bottom: 10px;
            }
        """)

        layout = QVBox()
        self.file_list = QListWidget()
        self.file_list.setStyleSheet("""
            QListWidget {
                background: transparent;
                color: #dcdcdc;
                outline: 0px;
                padding-left: 100px;
                padding-right: 100px;
                border: none;
            }

            QListWidget::item {
                background-color: rgb(40, 40, 40);
                margin-top: 10px;
                border: 1px solid rgb(50, 50, 50);
                border-radius: 10px;
            }

            QListWidget::item:hover {
                background-color: rgb(80, 80, 80);
                border: none;
            }

            QListWidget::item:selected {
                color: #dcdcdc;
                border: none;
            }
                                                 
            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 12px;
                margin-top: 13px;
                border-radius: 5px;
                margin-left: 10px;
                margin-bottom: 13px;
            }

            QScrollBar::handle:vertical {
                background-color: #383838;
                min-height: 30px;
                border-radius: 3px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #454545;
            }

            QScrollBar::handle:vertical:pressed {
                background-color: #424242;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        for filename, size_bytes in files_with_size:
            size_str = self.human_readable_size(size_bytes)
            item = QListWidgetItem()
            widget = FileSelectorItemWidget(parent=self.file_list, filename=filename, model_size=size_str, download_button_translation=download_button_translation, model_id=model_id)
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

        self.setStyleSheet("border: 1px solid rgb(50, 50, 55);")
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 30, 20, 30)
        layout.setSpacing(10)

        info_layout = QHBoxLayout()

        self.name_label = QLabel(f"<b>{filename}</b>")
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(9)
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.name_label.setFont(font)
        self.name_label.setMinimumHeight(30)
        self.name_label.setStyleSheet("color: rgb(227, 227, 227); font-weight: bold; font-size: 14px; background: transparent; border: none;")
        info_layout.addWidget(self.name_label)

        self.size_label = QLabel(f"({model_size})")
        self.size_label.setMinimumHeight(30)
        self.size_label.setStyleSheet("""
            color: rgb(227, 227, 227);
            border: none;
        """)
        info_layout.addWidget(self.size_label, stretch=1)

        btn_layout = QVBoxLayout()
        self.btn_download = QPushButton(download_button_translation)
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(9)
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.btn_download.setFont(font)
        icon_download = QtGui.QIcon()
        icon_download.addPixmap(QtGui.QPixmap("app/gui/icons/downloading.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.btn_download.setIconSize(QtCore.QSize(15, 15))
        self.btn_download.setIcon(icon_download)
        self.btn_download.setMinimumSize(160, 30)
        self.btn_download.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_download.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_download.setStyleSheet("""
            QPushButton {
                background-color: #2E2E2E;
                color: rgb(227, 227, 227);
                border-radius: 8px;
                font-size: 12px;
                border: 1px solid #444444;
            }

            QPushButton:hover {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                stop: 0 #3A3A3A, stop: 1 #2F2F2F);
                border: 1px solid #666666;
            }

            QPushButton:pressed {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                stop: 0 #2A2A2A, stop: 1 #444444);
                border: 1px solid #888888;
            }

            QPushButton:disabled {
                background-color: #222222;
                color: #777777;
                border: 1px solid #333333;
            }
        """)

        try:
            self.btn_download.clicked.disconnect()
        except TypeError:
            pass

        self.btn_download.clicked.connect(self.download_model_method)

        btn_layout.addWidget(self.btn_download)

        layout.addLayout(info_layout)
        layout.addLayout(btn_layout)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.setLayout(layout)
    
    def download_model_method(self):
        self.btn_download.setEnabled(False)
        self.btn_download.setText(" Downloading...")

        self.downloader_thread = FileDownloader(self.model_id, self.filename)
        self.downloader_thread.finished.connect(self.on_download_finished)
        self.downloader_thread.error.connect(self.on_download_error)
        self.downloader_thread.start()

    def on_download_finished(self, path):
        self.btn_download.setText(" Downloaded ✓")

    def on_download_error(self, error_msg):
        self.btn_download.setText(" Error")
        QtWidgets.QMessageBox.critical(self, "Download error", error_msg)

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