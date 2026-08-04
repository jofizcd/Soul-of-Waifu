import os
import json
import logging
import asyncio
import platform
import subprocess
import socket
import shlex
from pathlib import Path

import yaml
import psutil

from app.configuration import configuration

logger = logging.getLogger("Local Server Manager")

class LocalServerManager:
    """
    Manages the local launch of the LLM server (llama.cpp backend).
    Handles process creation, termination, lock files, and log streaming for UI feedback.
    """

    def __init__(self, ui=None):
        self.ui = ui
        self.configuration_settings = configuration.ConfigurationSettings()
        
        self.translations = {}
        selected_language = self.configuration_settings.get_main_setting("program_language")
        match selected_language:
            case 0:
                self.load_translation("en")
            case 1:
                self.load_translation("ru")

        self.server_process = None
        self.SERVER_PORT = 48596
        self.lock_file = Path(f"app/utils/ai_clients/backend/_temp/llama_server_{self.SERVER_PORT}.lock")
        
        self.restart_lock = asyncio.Lock()
        self.model_loaded = False

    def load_translation(self, language):
        file_path = f"app/translations/{language}.yaml"
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                self.translations = yaml.safe_load(file)
        else:
            self.translations = {}

    def is_port_available(self, port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                result = s.connect_ex(('localhost', port))
                return result != 0
        except Exception:
            return True

    def is_server_already_running(self):
        if self.lock_file.exists():
            try:
                with open(self.lock_file, 'r') as f:
                    lock_data = json.load(f)
                    pid = lock_data.get('pid')
                if pid and psutil.pid_exists(pid):
                    process = psutil.Process(pid)
                    cmd_line = ' '.join(process.cmdline()).lower()
                    if 'llama-server' in cmd_line:
                        logger.info(f"llama-server is already running with PID {pid}")
                        return True
                    else:
                        self.lock_file.unlink(missing_ok=True)
                else:
                    self.lock_file.unlink(missing_ok=True)
            except Exception:
                self.lock_file.unlink(missing_ok=True)

        if not self.is_port_available(self.SERVER_PORT):
            logger.info(f"Port {self.SERVER_PORT} appears to be in use")
            return True
        return False

    def create_lock_file(self):
        try:
            loop_time = asyncio.get_running_loop().time()
        except RuntimeError:
            loop_time = None

        lock_data = {
            'pid': os.getpid(),
            'port': self.SERVER_PORT,
            'timestamp': str(loop_time) if loop_time is not None else 'unknown'
        }
        try:
            self.lock_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.lock_file, 'w') as f:
                json.dump(lock_data, f)
        except Exception as e:
            logger.warning(f"Failed to create lock file: {e}")

    def cleanup_lock_file(self):
        try:
            if self.lock_file.exists():
                self.lock_file.unlink()
        except Exception as e:
            logger.warning(f"Couldn't delete lock file: {e}")

    def resolve_server_executable(self, llm_device, llm_backend):
        exe_suffix = ".exe" if platform.system() == "Windows" else ""
        current_server = None

        match llm_device:
            case 0:
                current_server = f"app/utils/ai_clients/backend/cpu/llama-server{exe_suffix}"
            case 1:
                match llm_backend:
                    case 0:
                        current_server = f"app/utils/ai_clients/backend/vulkan/llama-server{exe_suffix}"
                    case 1:
                        current_server = f"app/utils/ai_clients/backend/cuda/llama-server{exe_suffix}"
                    case 2:
                        current_server = f"app/utils/ai_clients/backend/hip/llama-server{exe_suffix}"
                    case 3:
                        current_server = f"app/utils/ai_clients/backend/sycl/llama-server{exe_suffix}"

        return current_server

    async def start_server_async(self):
        logger.info("Starting LLM server process...")
        await asyncio.sleep(1)
        
        if self.is_server_already_running():
            logger.warning("The server is already running by another process, connecting to it...")
            self.model_loaded = True
            self.update_ui_for_server_state(True)
            return

        model_path = self.configuration_settings.get_main_setting("local_llm")
        llm_device = self.configuration_settings.get_main_setting("llm_device")
        llm_backend = self.configuration_settings.get_main_setting("llm_backend")
        reasoning_mode = self.configuration_settings.get_main_setting("reasoning_mode")

        current_server = self.resolve_server_executable(llm_device, llm_backend)

        if current_server is None:
            logger.error(f"Unsupported llm_device={llm_device} / llm_backend={llm_backend} combination.")
            self.update_ui_for_server_state(False)
            raise RuntimeError(self.translations.get(
                "error_unsupported_backend",
                "Unsupported device/backend combination selected for the local model."
            ))

        if not Path(current_server).exists():
            logger.error(f"Server executable not found at: {current_server}")
            self.update_ui_for_server_state(False)
            raise RuntimeError(self.translations.get(
                "error_backend_not_found",
                f"Server executable not found: {current_server}"
            ))

        if not model_path or not Path(model_path).exists():
            logger.error(f"Model file not found: {model_path}")
            self.update_ui_for_server_state(False)
            raise RuntimeError(self.translations.get(
                "error_model_not_found",
                f"Model file not found: {model_path}"
            ))

        gpu_layers = self.configuration_settings.get_main_setting("gpu_layers")
        context_size = self.configuration_settings.get_main_setting("context_size")
        mlock_status = self.configuration_settings.get_main_setting("mlock_status")
        flash_attention = self.configuration_settings.get_main_setting("flash_attention_status")

        if self.server_process is not None:
            logger.warning("Server already running.")
            return

        c_arg = "0" if (context_size is None or context_size <= 0) else str(context_size)

        command = [
            current_server,
            "-m", model_path,
            "-c", c_arg,
            "--port", str(self.SERVER_PORT),
            "--parallel", "1",
        ]

        if reasoning_mode is False:
            command.extend(["--reasoning-budget", "0", "--reasoning", "off"])
            logger.info("Reasoning mode is disabled (--reasoning off + --reasoning-budget 0). Note: some models/quants ignore this flag; a <think> tag filter downstream is still recommended as a safety net.")

        chat_template = self.configuration_settings.get_main_setting("chat_template")
        if chat_template and chat_template.strip().lower() != "auto":
            template_flag = chat_template.strip().lower()
            command.extend(["--chat-template", template_flag])
            logger.info(f"Using forced Chat Template: {template_flag}")
        else:
            command.append("--jinja")
            logger.info("Using Auto Chat Template with native Jinja engine (--jinja).")

        if llm_device == 1:
            if gpu_layers is None or gpu_layers == 0:
                gpu_layers = 20
            command.extend(["--n-gpu-layers", str(gpu_layers)])
            logger.info(f"Using GPU with {gpu_layers} layers.")

            if flash_attention:
                command.extend(["-fa", "on"])
                logger.info("Flash Attention is enabled.")
        else:
            cpu_threads = self.configuration_settings.get_main_setting("cpu_threads")
            if cpu_threads and cpu_threads > 0:
                command.extend(["--threads", str(cpu_threads), "--threads-batch", str(cpu_threads)])
                logger.info(f"Using manual CPU Threads: {cpu_threads}")

        no_mmap_status = self.configuration_settings.get_main_setting("no_mmap_status")

        if mlock_status:
            command.extend(["--load-mode", "mlock"])
            logger.info("Model will be locked in RAM (mlock enabled).")
        elif no_mmap_status:
            command.extend(["--load-mode", "none"])
            logger.info("mmap disabled (--load-mode none).")

        kv_cache_type = self.configuration_settings.get_main_setting("kv_cache_type")
        if kv_cache_type and kv_cache_type != "f16":
            command.extend(["--cache-type-k", kv_cache_type, "--cache-type-v", kv_cache_type])
            logger.info(f"Using quantized KV Cache: {kv_cache_type}")

        batch_size = self.configuration_settings.get_main_setting("llm_batch_size")
        if batch_size and batch_size > 0:
            command.extend(["--batch-size", str(batch_size), "--ubatch-size", str(batch_size)])
            logger.info(f"Using prompt batch size: {batch_size}")
        
        cpu_moe_layers = self.configuration_settings.get_main_setting("cpu_moe_layers")
        if cpu_moe_layers and cpu_moe_layers > 0:
            command.extend(["--n-cpu-moe", str(cpu_moe_layers)])
            logger.info(f"MoE Offloading: Keeping experts of {cpu_moe_layers} layers in CPU RAM.")

        custom_args_str = self.configuration_settings.get_main_setting("custom_args")
        if custom_args_str and custom_args_str.strip():
            try:
                extra_args = shlex.split(custom_args_str)
                command.extend(extra_args)
                logger.info(f"Custom arguments added to command: {extra_args}")
            except Exception as e:
                logger.error(f"Error parsing custom arguments: {e}")

        logger.info(f"Executing server command: {' '.join(command)}")

        self.create_lock_file()

        try:
            self.server_process = await asyncio.create_subprocess_exec(
                *command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False
            )
        except Exception as e:
            logger.error(f"Failed to launch the server process: {e}", exc_info=True)
            self.cleanup_lock_file()
            self.update_ui_for_server_state(False)
            raise RuntimeError(self.translations.get(
                "error_server_launch_failed",
                f"Failed to launch the local server: {e}"
            ))

        asyncio.create_task(self.log_stream(self.server_process.stdout, logger.info))
        asyncio.create_task(self.log_stream(self.server_process.stderr, logger.info))

        await asyncio.sleep(1)

        if self.server_process.returncode is not None and self.server_process.returncode != 0:
            logger.error("Server failed to start.")
            self.server_process = None
            self.cleanup_lock_file()
            self.update_ui_for_server_state(False)
            raise RuntimeError(self.translations.get(
                "error_server_start_failed",
                "The local server process exited immediately after launch. Check the logs for details."
            ))
        else:
            logger.info("Server started successfully.")

    async def log_stream(self, stream, log_func):
        while True:
            line = await stream.readline()
            if not line:
                break
            try:
                decoded_line = line.decode("utf-8", errors="ignore").strip()
            except Exception:
                decoded_line = str(line, encoding="utf-8", errors="ignore").strip()
            
            log_func(decoded_line)

            if self.ui:
                try:
                    if not self.model_loaded:
                        if hasattr(self.ui, 'slide_in_status_container'):
                            self.ui.slide_in_status_container()
                        else:
                            self.ui.progressBar_llm_loading.show()
                            self.ui.loading_model_label.show()
                        
                        if hasattr(self.ui, 'update_system_status'):
                            self.ui.update_system_status("loading")
                    
                    if "load_model: loading model" in decoded_line and not self.model_loaded:
                        self.ui.progressBar_llm_loading.setValue(20)
                        self.ui.loading_model_label.setText(self.translations.get("model_loading_step_1", "ENGINE INIT..."))
                    
                    elif ("load:" in decoded_line or "W load:" in decoded_line) and not self.model_loaded:
                        self.ui.progressBar_llm_loading.setValue(40)
                        self.ui.loading_model_label.setText(self.translations.get("model_loading_step_2", "VERIFYING GGUF..."))

                    elif "load_model: initializing" in decoded_line and not self.model_loaded:
                        self.ui.progressBar_llm_loading.setValue(70)
                        self.ui.loading_model_label.setText(self.translations.get("model_loading_step_4", "ALLOCATING CONTEXT..."))
                    
                    elif "model loaded" in decoded_line and not self.model_loaded:
                        self.ui.progressBar_llm_loading.setValue(85)
                        self.ui.loading_model_label.setText(self.translations.get("model_loading_step_5", "FINALIZING..."))
                    
                    elif ("listening on http" in decoded_line or "all slots are idle" in decoded_line) and not self.model_loaded:
                        self.ui.progressBar_llm_loading.setValue(100)
                        self.ui.loading_model_label.setText(self.translations.get("model_loading_step_6", "MODEL ONLINE"))
                        self.model_loaded = True
                        self.update_ui_for_server_state(True)
                    
                    if self.model_loaded and "slot launch_slot_" in decoded_line:
                        if hasattr(self.ui, 'update_system_status'):
                            self.ui.update_system_status("generating")
                    
                    if self.model_loaded and ("slot      release:" in decoded_line or "all slots are idle" in decoded_line):
                        if hasattr(self.ui, 'update_system_status'):
                            self.ui.update_system_status("online")
                    
                    if hasattr(self.ui, 'lineEdit_server'):
                        self.ui.lineEdit_server.show()
                    
                except (RuntimeError, AttributeError) as e:
                    logger.debug(f"UI element no longer exists: {e}")
                    return

    def update_ui_for_server_state(self, is_running):
        if not self.ui:
            return
        try:
            if hasattr(self.ui, 'update_system_status'):
                if is_running and self.model_loaded:
                    self.ui.update_system_status("online")
                else:
                    self.ui.update_system_status("offline")

            if hasattr(self.ui, 'status_container'):
                if is_running:
                    from PyQt6.QtCore import QTimer
                    QTimer.singleShot(
                        3000, 
                        lambda: self.ui.slide_out_status_container() if (self.model_loaded and hasattr(self.ui, 'slide_out_status_container')) else None
                    )
                else:
                    if hasattr(self.ui, 'slide_out_status_container'):
                        self.ui.slide_out_status_container()
                    else:
                        self.ui.status_container.hide()
            else:
                if not is_running:
                    self.ui.progressBar_llm_loading.hide()
                    self.ui.loading_model_label.hide()
        except (RuntimeError, AttributeError) as e:
            logger.debug(f"UI updating error: {e}")

    async def stop_server(self):
        if self.server_process is None:
            logger.info("Server is not running.")
            self.update_ui_for_server_state(False)
            return

        logger.info("Stopping server...")

        try:
            try:
                self.server_process.terminate()
                await self.server_process.wait()
            except ProcessLookupError:
                logger.info("Local server process was already dead (likely crashed earlier).")

            self.server_process = None
            self.model_loaded = False
            self.cleanup_lock_file()
            self.update_ui_for_server_state(False)

            logger.info("The server has been successfully stopped.")
        except Exception as e:
            logger.error(f"Error when stopping the server: {e}", exc_info=True)

    async def ensure_server_running(self):
        async with self.restart_lock:
            if self.is_server_already_running():
                self.model_loaded = True
                self.update_ui_for_server_state(True)
                return
            
            if self.server_process is None:
                self.model_loaded = False
                await self.start_server_async()

                timeout = 360
                elapsed = 0
                
                while not self.model_loaded:
                    await asyncio.sleep(1)
                    elapsed += 1
                    
                    if self.server_process and self.server_process.returncode is not None:
                        logger.error(f"Server crashed with code {self.server_process.returncode}")
                        self.cleanup_lock_file()
                        self.update_ui_for_server_state(False)
                        raise RuntimeError("Local server crashed. Check logs (Out of memory?)")
                    
                    if elapsed > timeout:
                        logger.error("Server loading timed out.")
                        await self.stop_server()
                        raise RuntimeError("Server loading timed out.")

    async def shutdown_server_and_model(self):
        logger.info("Shutting down server and model...")
        await self.stop_server()
        self.update_ui_for_server_state(False)

    def _log_task_exception(self, task):
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Local server task failed: {e}", exc_info=True)
            self.update_ui_for_server_state(False)

    def on_shutdown_button_clicked(self):
        task = asyncio.create_task(self.shutdown_server_and_model())
        task.add_done_callback(self._log_task_exception)
    
    def on_start_server_button_clicked(self):
        task = asyncio.create_task(self.ensure_server_running())
        task.add_done_callback(self._log_task_exception)
