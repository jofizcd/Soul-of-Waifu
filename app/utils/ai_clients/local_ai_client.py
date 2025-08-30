import os
import json
import yaml
import psutil
import logging
import asyncio
import numpy as np
import subprocess
import socket

from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from openai import AsyncOpenAI
from pathlib import Path
from app.configuration import configuration

logger = logging.getLogger("Local LLM Client")

class LocalAI:
    """
    A class for managing the local launch of a Large Language Model (LLM) via a server,
    including model loading, server lifecycle control, and request handling.
    
    Features:
        - Starts/stops a local LLM server process
        - Communicates with the server via OpenAI-compatible API
        - Manages configuration settings for models, API, and UI
    """
    def __init__(self, ui=None):
        self.ui = ui
        
        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_characters = configuration.ConfigurationCharacters()

        self.translations = {}
        selected_language = self.configuration_settings.get_main_setting("program_language")
        match selected_language:
            case 0:
                self.load_translation("en")
            case 1:
                self.load_translation("ru")

        self.server_process = None
        self.SERVER_PORT = 8080
        self.lock_file = Path(f"app/utils/ai_clients/backend/_temp/llama_server_{self.SERVER_PORT}.lock")
        
        self.shutdown_task = None
        self.restart_lock = asyncio.Lock()
        self.model_loaded = False
        
        self.ui_initialized = False

    def load_translation(self, language):
        """
        Loads translation strings from a YAML file based on the language code.
        """
        file_path = f"app/translations/{language}.yaml"
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                self.translations = yaml.safe_load(file)
        else:
            self.translations = {}
    
    def is_port_available(self, port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('localhost', port))
                return True
        except OSError:
            return False

    def is_server_already_running(self):
        """
        Checks whether the server is already running on this port by another process.
        """
        if self.lock_file.exists():
            try:
                with open(self.lock_file, 'r') as f:
                    lock_data = json.load(f)
                    pid = lock_data.get('pid')

                if pid and psutil.pid_exists(pid):
                    process = psutil.Process(pid)
                    if 'server' in ' '.join(process.cmdline()).lower():
                        logger.info(f"Server is already running with a PID {pid}")
                        return True
                else:
                    self.lock_file.unlink(missing_ok=True)
            except (json.JSONDecodeError, KeyError, psutil.NoSuchProcess, PermissionError):
                self.lock_file.unlink(missing_ok=True)

        if not self.is_port_available(self.SERVER_PORT):
            logger.info(f"Port {self.SERVER_PORT} appears to be in use (possibly in TIME_WAIT state)")
            return True
            
        return False

    def create_lock_file(self):
        """
        Creates a lock file to prevent multiple servers from running.
        """
        lock_data = {
            'pid': os.getpid(),
            'port': self.SERVER_PORT,
            'timestamp': str(asyncio.get_event_loop().time()) if asyncio.get_event_loop() else 'unknown'
        }
        try:
            with open(self.lock_file, 'w') as f:
                json.dump(lock_data, f)
        except Exception as e:
            logger.warning(f"Failed to create a lock file: {e}")

    def cleanup_lock_file(self):
        """
        Deletes the lock file.
        """
        try:
            if self.lock_file.exists():
                self.lock_file.unlink()
        except Exception as e:
            logger.warning(f"Couldn't delete the lock file: {e}")
    
    def cleanup_ui_resources(self):
        if self.ui and hasattr(self.ui, 'pushButton_turn_off_llm'):
            try:
                if self.ui.pushButton_turn_off_llm is not None:
                    try:
                        self.ui.pushButton_turn_off_llm.clicked.disconnect()
                    except (TypeError, RuntimeError):
                        pass

                    self.ui.pushButton_turn_off_llm = None
            except RuntimeError:
                self.ui.pushButton_turn_off_llm = None
        
        if self.ui:
            try:
                self.ui.progressBar_llm_loading.hide()
                self.ui.loading_model_label.hide()
            except (AttributeError, RuntimeError):
                pass
    
    async def start_server_async(self):
        """
        Asynchronously starts the local LLM server process with configured model and settings.
        
        This method builds a command line based on current configuration values and launches
        the appropriate server binary depending on selected device (CPU or GPU) and backend.
        """
        logger.info("Starting LLM server process...")

        await asyncio.sleep(1)
        
        if self.is_server_already_running():
            logger.warning("The server is already running by another process, connecting to it...")
            self.model_loaded = True
            return

        model_path = self.configuration_settings.get_main_setting("local_llm")
        llm_device = self.configuration_settings.get_main_setting("llm_device")
        llm_backend = self.configuration_settings.get_main_setting("llm_backend")

        current_server = None
        match llm_device:
            case 0: # CPU MODE
                current_server = "app/utils/ai_clients/backend/cpu/server.exe"
            case 1:
                match llm_backend:
                    case 0: # VULKAN MODE
                        current_server = "app/utils/ai_clients/backend/vulkan/server.exe"
                    case 1: # CUDA MODE
                        current_server = "app/utils/ai_clients/backend/cuda/server.exe"
        
        gpu_layers = self.configuration_settings.get_main_setting("gpu_layers")
        context_size = self.configuration_settings.get_main_setting("context_size")
        mlock_status = self.configuration_settings.get_main_setting("mlock_status")
        flash_attention = self.configuration_settings.get_main_setting("flash_attention_status")

        if self.server_process is not None:
            logger.warning("Server already running.")
            return

        command = [
            current_server,
            "-m", model_path,                  # Model path
            "-c", str(context_size),           # Context size
            "--port", str(self.SERVER_PORT),   # Server port
        ]

        if llm_device == 1:
            if gpu_layers is None or gpu_layers == 0:
                gpu_layers = 20
            command.extend(["--n-gpu-layers", str(gpu_layers)])
            logger.info(f"Using GPU with {gpu_layers} layers.")

            if flash_attention == True:
                command.append("-fa")
                logger.info("Flash Attention is enabled.")
        else:
            logger.info("Using CPU.")

        if mlock_status:
            command.append("--mlock")
            logger.info("Model will be locked in RAM (mlock enabled).")

        logger.info(f"Executing server command: {' '.join(command)}")

        self.create_lock_file()

        self.server_process = await asyncio.create_subprocess_exec(
            *command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False
        )

        asyncio.create_task(self.log_stream(self.server_process.stdout, logger.info))
        asyncio.create_task(self.log_stream(self.server_process.stderr, logger.info))

        await asyncio.sleep(1)

        if self.server_process.returncode is not None and self.server_process.returncode != 0:
            logger.error("Server failed to start.")
            self.cleanup_lock_file()
            raise RuntimeError("Server failed to start.")
        else:
            logger.info("Server started successfully.")
    
    async def log_stream(self, stream, log_func):
        while True:
            line = await stream.readline()
            if not line:
                break
            try:
                decoded_line = line.decode("utf-8", errors="ignore").strip()
            except Exception as e:
                decoded_line = str(line, encoding="utf-8", errors="ignore").strip()
            log_func(decoded_line)

            if self.ui and hasattr(self.ui, 'pushButton_turn_off_llm'):
                try:
                    if self.ui.pushButton_turn_off_llm is None:
                        return
                        
                    self.ui.progressBar_llm_loading.show()
                    self.ui.loading_model_label.show()
                    
                    if "main: loading model" in decoded_line:
                        self.ui.progressBar_llm_loading.setValue(20)
                        self.ui.loading_model_label.setText(self.translations.get("model_loading_step_1", "Starting loading the model"))
                    
                    elif "print_info: file format" in decoded_line:
                        self.ui.progressBar_llm_loading.setValue(40)
                        self.ui.loading_model_label.setText(self.translations.get("model_loading_step_2", "Checking the file format"))

                    elif "load_tensors: loading model tensors" in decoded_line:
                        self.ui.progressBar_llm_loading.setValue(50)
                        self.ui.loading_model_label.setText(self.translations.get("model_loading_step_3", "Loading model tensors"))
                    
                    elif "llama_context: constructing llama_context" in decoded_line:
                        self.ui.progressBar_llm_loading.setValue(70)
                        self.ui.loading_model_label.setText(self.translations.get("model_loading_step_4", "Constructing llama context"))
                    
                    elif "main: model loaded" in decoded_line and not self.model_loaded:
                        self.ui.progressBar_llm_loading.setValue(85)
                        self.ui.loading_model_label.setText(self.translations.get("model_loading_step_5", "Model is almost loaded"))
                    
                    elif "all slots are idle" in decoded_line:
                        self.ui.progressBar_llm_loading.setValue(100)
                        self.ui.loading_model_label.setText(self.translations.get("model_loading_step_6", "Model is ready to work"))
                    
                    if hasattr(self.ui.pushButton_turn_off_llm, 'clicked'):
                        try:
                            self.ui.pushButton_turn_off_llm.clicked.disconnect()
                        except (TypeError, RuntimeError):
                            pass
                        self.ui.pushButton_turn_off_llm.clicked.connect(self.on_shutdown_button_clicked)   
                        self.ui.pushButton_turn_off_llm.setText(self.translations.get("turn_off_llm", " Shutdown Model"))
                        self.ui.pushButton_turn_off_llm.show()

                    self.ui.lineEdit_server.show()
                    
                except (RuntimeError, AttributeError) as e:
                    logger.debug(f"UI element no longer exists: {e}")
                    return

            self.model_loaded = True

    async def stop_server(self):
        """
        Stops the running LLM server process.
        
        If the server is running, it sends a termination signal and waits for graceful shutdown.
        Cleans up internal state after successful termination.
        """
        if self.server_process is None:
            logger.info("Server is not running.")
            return

        logger.info("Stopping server...")

        try:
            self.server_process.terminate()
            await self.server_process.wait()

            self.server_process = None
            self.model_loaded = False
            self.cleanup_lock_file()

            logger.info("The server has been successfully stopped.")
        except Exception as e:
            logger.error(f"Error when stopping the server: {e}", exc_info=True)

    async def ensure_server_running(self):
        """
        Ensures that the server is running and a model is loaded.
        
        If the server is not running, starts it and waits until the model is fully loaded.
        Uses a lock to prevent multiple simultaneous restart attempts.
        """
        async with self.restart_lock:
            if self.is_server_already_running():
                self.model_loaded = True
                return
            
            if self.server_process is None:
                self.model_loaded = False
                await self.start_server_async()

                while not self.model_loaded:
                    await asyncio.sleep(1)

    def build_system_prompt(self, character_name, user_name, user_description, chat_messages, user_message):
        """
        Builds a system prompt based on the order from the preset, 
        with substitution of person data, lorebook, and author's notes.
        """
        config = self.configuration_settings.load_configuration()
        user_data = config.get("user_data", {})
        smart_memory = self.configuration_settings.get_main_setting("smart_memory")

        character_data = self.configuration_characters.load_configuration()
        character_list = character_data.get("character_list", {})
        character_information = character_list.get(character_name, {})

        selected_persona = character_information.get("selected_persona", "None")
        selected_preset = character_information.get("selected_system_prompt_preset", "By default")
        selected_lorebook = character_information.get("selected_lorebook", "None")

        personas = user_data.get("personas", {})
        presets = user_data.get("presets", {})
        lorebooks = user_data.get("lorebooks", {})
        author_notes = user_data.get("author_notes", "")

        if selected_preset == "By default":
            system_prompt_template = (
                "This is a neverending story between {{user}} who is {{user_description}}, {{char}}, and whatever other characters present in said story. "
                "This story has some basic guidelines that need to be respected in every message from {{char}}: Temporal, emotional and logical coherence is very important. "
                "Focus on it, but keep some dynamism. Use the context to understand {{char}}, and keep the outputs in-character. "
                "Descriptions from {{char}}'s point of view are great, focusing on other characters' appearance, words, the sounds and the smells. "
                "Explicit language is encouraged. Sensitive and sexual content are expected. Immoral and illicit subjects are allowed. "
                "Follow the formatting of previous responses, and reply with a length of random: 10-80, 100-150, 150-220, ~300 words per response. "
                "Avoid speaking and acting for {{user}}."
            )
            order = [
                "System prompt",
                "Character's information",
                "Lorebook",
                "Persona information",
                "Author's notes"
            ]
        else:
            preset = presets.get(selected_preset, {})
            system_prompt_template = preset.get("prompt", "")
            order = preset.get("order", [])

        replacements = {
            "{{user}}": user_name,
            "{{char}}": character_name,
            "{{user_description}}": user_description
        }

        system_prompt_parts = []

        for section in order:
            match section:
                case "System prompt":
                    part = system_prompt_template
                    for key, value in replacements.items():
                        part = part.replace(key, value)
                    system_prompt_parts.append({
                        "role": "system",
                        "content": part
                    })

                case "Character's information":
                    char_info = character_information.get("character_information", "")
                    if char_info:
                        system_prompt_parts.append({
                            "role": "system",
                            "content": f"[CHARACTER PROFILE]\n{char_info}"
                        })

                case "Persona information":
                    if selected_persona != "None" and selected_persona in personas:
                        persona = personas[selected_persona]
                        persona_text = (
                            f"User Name: {persona['user_name']}\n"
                            f"User Description: {persona['user_description']}"
                        )
                        system_prompt_parts.append({
                            "role": "system",
                            "content": "[USER PROFILE]\n" + persona_text
                        })

                case "Lorebook":
                    if selected_lorebook != "None" and selected_lorebook in lorebooks:
                        activated_entries = self.get_activated_lorebook_entries(selected_lorebook, chat_messages)
                        if activated_entries:
                            lorebook_content = "\n\n".join([
                                f"[ENTRY №{idx}]\n{content}" 
                                for idx, content in enumerate(activated_entries, start=1)
                            ])
                            system_prompt_parts.append({
                                "role": "system",
                                "content": "[LOREBOOK]\n" + lorebook_content
                            })

                case "Author's notes":
                    if author_notes.strip():
                        system_prompt_parts.append({
                            "role": "system",
                            "content": "[AUTHOR NOTES]\n" + author_notes
                        })

        if not smart_memory:
            system_prompt_parts.extend(chat_messages)
        else:
            if len(chat_messages) < 10:
                system_prompt_parts.extend(chat_messages)
            else:
                try:
                    model = SentenceTransformer('app/utils/all-MiniLM-L6-v2')

                    MIN_SEGMENT_WORDS = 10
                    TOP_RELEVANT_FRAGMENTS = 4
                    SHORT_TERM_DEPTH = 3

                    dynamic_history_depth = max(20, min(int(len(chat_messages) * 0.3), 200))

                    if len(chat_messages) > 500:
                        dynamic_history_depth = min(dynamic_history_depth + 100, len(chat_messages))

                    segments = []
                    current_segment = []

                    for msg in chat_messages[-dynamic_history_depth:]:
                        role = msg["role"]
                        content = msg["content"].strip()
                        
                        if not content:
                            continue

                        if current_segment and current_segment[-1]["role"] != role:
                            segment_text = " ".join([m["content"] for m in current_segment])
                            if len(segment_text.split()) >= MIN_SEGMENT_WORDS:
                                segments.append({
                                    "messages": current_segment.copy(),
                                    "text": segment_text
                                })
                            current_segment = []
                        
                        current_segment.append(msg)

                    if current_segment:
                        segment_text = " ".join([m["content"] for m in current_segment])
                        if len(segment_text.split()) >= MIN_SEGMENT_WORDS:
                            segments.append({
                                "messages": current_segment,
                                "text": segment_text
                            })

                    if len(segments) < 2:
                        system_prompt_parts.extend(chat_messages)
                        return system_prompt_parts
                    
                    segment_texts = [seg["text"] for seg in segments]

                    segment_embeddings = model.encode(segment_texts, convert_to_tensor=True)
                    query_embedding = model.encode([user_message], convert_to_tensor=True)

                    similarities = cosine_similarity(
                        query_embedding.cpu().numpy(),
                        segment_embeddings.cpu().numpy()
                    )[0]

                    top_indices = np.argsort(similarities)[-TOP_RELEVANT_FRAGMENTS:][::-1]

                    memory_fragments = []
                    for i, idx in enumerate(top_indices):
                        seg = segments[idx]
                        fragment = f"[MEMORY FRAGMENT #{i+1}]\n"
                        for msg in seg["messages"]:
                            role = "USER" if msg["role"] == "user" else character_name.upper()
                            fragment += f"{role}: {msg['content'].strip()}\n"
                        memory_fragments.append(fragment.strip())

                    if memory_fragments:
                        system_prompt_parts.append({
                            "role": "system",
                            "content": f"[LONG-TERM MEMORY]\n" + "\n\n".join(memory_fragments)
                        })

                    system_prompt_parts.append({
                        "role": "system",
                        "content": "[SHORT-TERM MEMORY]\n"
                    })
                    system_prompt_parts.extend(chat_messages[-SHORT_TERM_DEPTH:])
                    
                except Exception as e:
                    logger.error(f"Smart memory error: {str(e)}")
                    system_prompt_parts.extend(chat_messages)

        return system_prompt_parts

    def get_activated_lorebook_entries(self, lorebook_name, chat_messages):
        """
        Retrieves a list of activated entries from the specified lorebook, 
        based on the depth of the scan and the presence of keywords in the chat.
        """
        config = self.configuration_settings.load_configuration()
        lorebooks = config.get("user_data", {}).get("lorebooks", {})

        if lorebook_name not in lorebooks:
            return []

        lorebook = lorebooks[lorebook_name]
        scan_depth = lorebook.get("n_depth", 3)
        entries = lorebook.get("entries", [])

        if scan_depth == 0:
            relevant_messages = []
        else:
            relevant_messages = chat_messages[-scan_depth:]

        context_text = " ".join([msg["content"] for msg in relevant_messages]).lower()

        activated_entries = []

        for entry in entries:
            keys = entry.get("key", [])
            for key in keys:
                if key.lower() in context_text:
                    activated_entries.append(entry["content"])
                    break

        return activated_entries
    
    async def send_message(self, context_messages, user_message, character_name, user_name, user_description):
        """
        Sends a message to the local LLM server and streams the response back in real-time.
        
        This method ensures the server is running, prepares the full prompt with context,
        sends the request using an OpenAI-compatible interface, and yields the result as it arrives.

        Args:
            character_information (str): Core personality/instructions for the character.
            context_messages (list): List of previous conversation messages.
            user_message (str): Current input from the user.
            character_name (str): Name of the AI character.
            user_name (str): Name of the user.
            user_description (str): Description of the user for context.

        Yields:
            str: Chunks of generated text as they are received from the server.
        """
        await self.ensure_server_running()      

        max_tokens = self.configuration_settings.get_main_setting("max_tokens")
        temperature = self.configuration_settings.get_main_setting("temperature")
        top_p = self.configuration_settings.get_main_setting("top_p")
        repeat_penalty = self.configuration_settings.get_main_setting("repeat_penalty")

        final_system_prompt = self.build_system_prompt(
            character_name=character_name,
            user_name=user_name,
            user_description=user_description,
            chat_messages=context_messages,
            user_message=user_message
        )

        new_user_message = {"role": "user", "content": user_message}

        messages = final_system_prompt + [new_user_message]

        logger.info(messages)

        client = AsyncOpenAI(
            base_url=f"http://localhost:{self.SERVER_PORT}/v1",
            api_key="no-key-required"
        )
        
        completion = await client.chat.completions.create(
            model="openai/gpt-4o",
            messages=messages,
            stream=True,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            frequency_penalty=repeat_penalty,
            presence_penalty=0.7,
            stop=["<|im_end|>"]
        )

        try:
            async for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Request error: {e}")
            yield f"\nGeneration stopped."

    async def shutdown_server_and_model(self):
        """
        Gracefully shuts down the local LLM server and performs cleanup of UI elements.
        
        Cancels any pending shutdown task, stops the server process,
        and hides related UI components to reflect the inactive state.
        """
        logger.info("Shutting down server and model...")

        if self.shutdown_task and not self.shutdown_task.done():
            self.shutdown_task.cancel()
            logger.debug("Previous shutdown task cancelled.")
        
        await self.stop_server()

        if self.ui and hasattr(self.ui, 'pushButton_turn_off_llm'):
            try:
                if self.ui.pushButton_turn_off_llm is not None:
                    try:
                        self.ui.pushButton_turn_off_llm.clicked.disconnect()
                    except (TypeError, RuntimeError):
                        pass
                    self.ui.pushButton_turn_off_llm = None
            except RuntimeError:
                self.ui.pushButton_turn_off_llm = None
        
        if self.ui:
            try:
                self.ui.progressBar_llm_loading.hide()
                self.ui.loading_model_label.hide()
            except (AttributeError, RuntimeError):
                pass

    def on_shutdown_button_clicked(self):
        asyncio.create_task(self.shutdown_server_and_model())
    
    def on_start_server_button_clicked(self):
        asyncio.create_task(self.ensure_server_running())