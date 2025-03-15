import json
import time
import logging
import asyncio
import aiohttp
import subprocess

from configuration import configuration

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("resources\\data\\logs\\sow.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LocalAI:
    def __init__(self):
        # Initialize configurations
        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_characters = configuration.ConfigurationCharacters()

        # Server and model configuration
        self.server_process = None
        self.SERVER_PORT = 8080
        self.SERVER_EXE = "api_clients/server/server.exe"
        self.MODEL_PATH = self.configuration_settings.get_main_setting("local_llm")
        self.llm_device = self.configuration_settings.get_main_setting("llm_device")
        self.gpu_layers = self.configuration_settings.get_main_setting("gpu_layers")

        self.inactivity_timeout = 60  # 1 минута (в секундах)
        self.shutdown_task = None  # Задача для отслеживания неактивности
        self.restart_lock = asyncio.Lock()  # Блокировка для предотвращения гонок

    async def _start_server_async(self):
        if self.server_process is not None:
            logger.info("Server is already running.")
            return

        command = [
            self.SERVER_EXE,
            "-m", self.MODEL_PATH,
            "--port", str(self.SERVER_PORT),
        ]
        mlock_status = self.configuration_settings.get_main_setting("mlock_status")
        if self.llm_device == 1:
            if self.gpu_layers is None or self.gpu_layers == 0:
                self.gpu_layers = 25
            command.extend(["--n-gpu-layers", str(self.gpu_layers)])
            logger.info(f"Using GPU with {self.gpu_layers} layers.")
        else:
            logger.info("Using CPU.")

        if mlock_status:
            command.append("--mlock")
            logger.info("Using mlock to load the model into RAM.")

        logger.info(f"Starting server: {' '.join(command)}")
        self.server_process = await asyncio.create_subprocess_exec(
            *command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False
        )

        async def log_output(stream, log_func):
            while True:
                line = await stream.readline()
                if line:
                    log_func(line.decode("utf-8").strip())
                else:
                    break

        asyncio.create_task(log_output(self.server_process.stdout, logger.info))
        asyncio.create_task(log_output(self.server_process.stderr, logger.info))

        await asyncio.sleep(15)
        if self.server_process.returncode is not None:
            logger.error("Server failed to start.")
            raise RuntimeError("Server failed to start.")
        else:
            logger.info("Server started successfully.")
    
    async def stop_server(self):
        """
        Останавливает сервер, если он запущен.
        """
        if self.server_process is None:
            logger.info("Server is not running.")
            return

        logger.info("Stopping server...")
        try:
            self.server_process.terminate()
            await self.server_process.wait()
            self.server_process = None
            logger.info("Server stopped successfully.")
        except Exception as e:
            logger.error(f"Error stopping server: {e}")
    
    async def schedule_shutdown(self):
        """
        Планирует остановку сервера через заданное время.
        """
        await asyncio.sleep(self.inactivity_timeout)
        if self.server_process:
            logger.info("Server has been inactive for too long. Stopping it.")
            await self.stop_server()

    def reset_shutdown_timer(self):
        """
        Сбрасывает таймер неактивности.
        """
        if self.shutdown_task:
            self.shutdown_task.cancel()  # Отменяем текущий таймер
            logger.debug("Cancelled previous shutdown task.")
        self.shutdown_task = asyncio.create_task(self.schedule_shutdown())
        logger.debug("Scheduled new shutdown task.")

    async def ensure_server_running(self):
        """
        Убеждается, что сервер запущен перед выполнением запроса.
        """
        async with self.restart_lock:  # Предотвращаем гонку при запуске сервера
            if self.server_process is None:
                logger.info("Server is not running. Starting it...")
                await self._start_server_async()
                await self._wait_for_server_ready()
    
    async def _wait_for_server_ready(self):
        """
        Проверяет, готов ли сервер принимать запросы.
        """
        url = f"http://localhost:{self.SERVER_PORT}/"
        timeout = aiohttp.ClientTimeout(total=5)
        max_retries = 10
        retries = 0

        while retries < max_retries:
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            logger.info("Server is ready.")
                            return True
            except Exception as e:
                logger.info(f"Server not ready yet: {e}")
            
            retries += 1
            await asyncio.sleep(2)

        logger.error("Server failed to become ready after multiple attempts.")
        raise TimeoutError("Server did not become ready in time.")

    async def send_message(self, system_prompt, context, user_message, character_name, user_name):
        """
        Asynchronously sends a user message and streams the response from the model.
        """
        self.reset_shutdown_timer()  # Сбрасываем таймер неактивности
        await self.ensure_server_running()  # Убеждаемся, что сервер запущен

        # Generation parameters
        max_tokens = self.configuration_settings.get_main_setting("max_tokens")
        temperature = self.configuration_settings.get_main_setting("temperature")
        top_p = self.configuration_settings.get_main_setting("top_p")
        repeat_penalty = self.configuration_settings.get_main_setting("repeat_penalty")
        logger.info(f"Generation parameters: max_tokens={max_tokens}, temperature={temperature}, top_p={top_p}, repeat_penalty={repeat_penalty}")

        current_prompt = f"""
        <bos><start_of_turn>user
        <instructions>
        You are a {character_name}. {system_prompt}
        Write {character_name}'s next reply in a fictional chat between {character_name} and {user_name}. Write 1 reply only in internet RP style, italicize actions, and avoid quotation marks. Use markdown. Be proactive, creative, and drive the plot and conversation forward. Write at least 1 paragraph. Always stay in character and avoid repetition. Do not write any text on behalf of {user_name}.
        </instructions>
        </start_of_turn>
        <start_of_turn>model
        """

        full_prompt = current_prompt + context + f"<start_of_turn>user\n{user_message}</start_of_turn>\n<start_of_turn>model\n"
        logger.debug(f"Generated prompt: {full_prompt}")

        payload = {
            "prompt": f"{full_prompt}",
            "n_predict": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "repeat_penalty": repeat_penalty,
            "stop": ["</start_of_turn>", "</start_of>turn"],
            "stream": True
        }

        max_retries = 3
        retry_delay = 2
        for attempt in range(max_retries):
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"http://localhost:{self.SERVER_PORT}/completion",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status == 200:
                        logger.info("Request processed successfully.")
                        buffer = ""
                        async for line in response.content:
                            if line:
                                try:
                                    buffer += line.decode("utf-8")
                                    while "\n" in buffer:
                                        line_data, buffer = buffer.split("\n", 1)
                                        if line_data.startswith("data: "):
                                            json_data = line_data[len("data: "):]
                                            chunk_data = json.loads(json_data)
                                            if chunk_data.get("content"):
                                                yield chunk_data["content"]
                                except json.JSONDecodeError as e:
                                    logger.error(f"JSON decoding error: {line}")
                                    yield f"Error: invalid server response ({e})"
                        return
                    elif response.status == 503 and attempt < max_retries - 1:
                        logger.warning(f"Server returned 503. Retrying in {retry_delay} seconds...")
                        await asyncio.sleep(retry_delay)
                    else:
                        error_message = await response.text()
                        logger.error(f"Error: {response.status}, {error_message}")
                        yield f"Error: server returned status {response.status}"
                        return