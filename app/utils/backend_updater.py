import os
import json
import shutil
import zipfile
import asyncio
import aiohttp
import logging
from pathlib import Path
from PyQt6 import QtCore, QtGui, QtWidgets

logger = logging.getLogger("LlamaUpdater")

class LlamaUpdater(QtCore.QObject):
    progress_signal = QtCore.pyqtSignal(int, str)
    finished_signal = QtCore.pyqtSignal(bool, str)

    def __init__(self, backend_dir: Path):
        super().__init__()
        self.backend_dir = backend_dir
        self.cache_dir = backend_dir / "_update_cache"
        self.backup_dir = backend_dir / "_backup"
        self.version_file = backend_dir / "version.json"
        self.github_api_url = "https://api.github.com/repos/ggerganov/llama.cpp/releases/latest"

    async def fetch_latest_release(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.github_api_url, timeout=10) as response:
                    if response.status != 200:
                        return None, f"GitHub API error: HTTP {response.status}"
                    data = await response.json()
                    return data, None
        except Exception as e:
            return None, str(e)

    def _get_current_version(self, backend_type: str) -> str:
        if self.version_file.exists():
            try:
                data = json.loads(self.version_file.read_text())
                return data.get(backend_type.lower(), "unknown")
            except Exception:
                pass
        return "unknown"

    def _match_assets(self, assets: list, backend_type: str) -> list:
        matched_urls = []
        backend_type = backend_type.lower()
        
        def matches(name, keywords):
            return all(kw in name for kw in keywords) and "arm64" not in name

        for asset in assets:
            name = asset.get("name", "").lower()
            if asset.get("content_type") not in ["application/zip", "application/x-zip-compressed"] and not name.endswith(".zip"):
                continue

            if backend_type == "cpu" and matches(name, ["llama", "win", "cpu", "x64"]):
                matched_urls.append(asset["browser_download_url"])
            
            elif backend_type == "cuda":
                if matches(name, ["llama", "win", "cuda", "12", "x64"]):
                    matched_urls.append(asset["browser_download_url"])
                elif matches(name, ["cudart", "win", "cuda", "12", "x64"]):
                    matched_urls.append(asset["browser_download_url"])
            
            elif backend_type == "vulkan" and matches(name, ["llama", "win", "vulkan", "x64"]):
                matched_urls.append(asset["browser_download_url"])
            
            elif backend_type == "hip" and matches(name, ["llama", "win", "hip", "radeon", "x64"]):
                matched_urls.append(asset["browser_download_url"])
            
            elif backend_type == "sycl" and matches(name, ["llama", "win", "sycl", "x64"]):
                matched_urls.append(asset["browser_download_url"])
                
        return matched_urls

    async def download_and_install(self, asset_urls: list, backend_type: str, version_tag: str):
        target_folder = self.backend_dir / backend_type.lower()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self._create_backup(target_folder)
        target_folder.mkdir(parents=True, exist_ok=True)

        try:
            for idx, url in enumerate(asset_urls):
                zip_path = self.cache_dir / f"update_{idx}.zip"
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status != 200:
                            raise Exception(f"Failed to download file from {url}")

                        total_size = int(response.headers.get('content-length', 0))
                        downloaded = 0
                        
                        with open(zip_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total_size:
                                    percent = int((downloaded / total_size) * 100)
                                    self.progress_signal.emit(percent, f"Downloading part [{idx+1}/{len(asset_urls)}]... {downloaded//1024//1024}MB / {total_size//1024//1024}MB")

                self.progress_signal.emit(100, f"Extracting part [{idx+1}/{len(asset_urls)}]...")
                await asyncio.sleep(0.5)

                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    for file_info in zip_ref.infolist():
                        if file_info.filename.endswith(('.exe', '.dll')):
                            filename = Path(file_info.filename).name
                            extracted_path = target_folder / filename
                            
                            if extracted_path.exists():
                                os.remove(extracted_path)
                                
                            with zip_ref.open(file_info) as source, open(extracted_path, "wb") as target:
                                shutil.copyfileobj(source, target)
                                
                if zip_path.exists():
                    os.remove(zip_path)

            ver_data = {}
            if self.version_file.exists():
                try:
                    ver_data = json.loads(self.version_file.read_text())
                except Exception:
                    pass
            
            ver_data[backend_type.lower()] = version_tag
            
            self.version_file.write_text(json.dumps(ver_data, indent=4))
            
            self.finished_signal.emit(True, f"Successfully updated {backend_type.upper()} engine to {version_tag}!")

        except PermissionError:
            self.finished_signal.emit(False, "Permission Denied! Ensure the LLM server is STOPPED.")
            await self.restore_backup(backend_type)
        except Exception as e:
            self.finished_signal.emit(False, f"Update error: {e}")
            await self.restore_backup(backend_type)

    def _create_backup(self, target_folder: Path):
        if not target_folder.exists():
            return
        
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        backup_folder = self.backup_dir / target_folder.name
        
        if backup_folder.exists():
            shutil.rmtree(backup_folder)
        
        shutil.copytree(target_folder, backup_folder)
        logger.info(f"Backup created for {target_folder.name}")

    async def restore_backup(self, backend_type: str):
        target_folder = self.backend_dir / backend_type.lower()
        backup_folder = self.backup_dir / backend_type.lower()
        
        if not backup_folder.exists():
            return False, "No backup found for this backend."

        try:
            if target_folder.exists():
                shutil.rmtree(target_folder)
            shutil.copytree(backup_folder, target_folder)
            return True, "Successfully reverted to the previous version!"
        except Exception as e:
            return False, f"Failed to restore backup: {e}"