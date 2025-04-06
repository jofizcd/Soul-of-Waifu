import logging
import asyncio
import aiohttp
import subprocess

from openai import AsyncOpenAI
from configuration import configuration

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("resources\\data\\logs\\local_llm.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LocalAI:
    def __init__(self, ui=None):
        self.ui = ui
        
        # Initialize configurations
        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_characters = configuration.ConfigurationCharacters()

        # Server and model configuration
        self.server_process = None
        self.SERVER_PORT = 8080
        self.SERVER_EXE = "api_clients/server/server.exe"

        self.shutdown_task = None
        self.restart_lock = asyncio.Lock()

    async def _start_server_async(self):
        self.MODEL_PATH = self.configuration_settings.get_main_setting("local_llm")
        self.llm_device = self.configuration_settings.get_main_setting("llm_device")
        self.gpu_layers = self.configuration_settings.get_main_setting("gpu_layers")

        if self.server_process is not None:
            print("Server is already running.")
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
            print(f"Using GPU with {self.gpu_layers} layers.")
        else:
            print("Using CPU.")

        if mlock_status:
            command.append("--mlock")
            print("Using mlock to load the model into RAM.")

        print(f"Starting server: {' '.join(command)}")
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

        if self.server_process.returncode is not None:
            print("Server failed to start.")
            raise RuntimeError("Server failed to start.")
        else:
            print("Server started successfully.")
    
    async def stop_server(self):
        if self.server_process is None:
            print("Server is not running.")
            return

        print("Stopping server...")
        try:
            self.server_process.terminate()
            await self.server_process.wait()
            self.server_process = None
            print("Server stopped successfully.")
        except Exception as e:
            print(f"Error stopping server: {e}")

    async def ensure_server_running(self):
        async with self.restart_lock:
            if self.server_process is None:
                print("Server is not running. Starting it...")
                await self._start_server_async()
                await self._wait_for_server_ready()
    
    async def _wait_for_server_ready(self):
        url = f"http://localhost:{self.SERVER_PORT}/"
        timeout = aiohttp.ClientTimeout(total=5)
        max_retries = 30
        retries = 0

        while retries < max_retries:
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            print("Server is ready.")
                            return True
            except Exception as e:
                print(f"Server not ready yet: {e}")
            
            retries += 1
            await asyncio.sleep(2)

        print("Server failed to become ready after multiple attempts.")
        raise TimeoutError("Server did not become ready in time.")

    async def send_message(self, system_prompt, context_messages, user_message, character_name, user_name, user_description):
        """
        Asynchronously sends a user message and streams the response from the model.
        """
        await self.ensure_server_running()
        self.ui.pushButton_turn_off_llm.show()
        self.ui.pushButton_turn_off_llm.clicked.connect(self.on_shutdown_button_clicked)

        # Generation parameters
        max_tokens = self.configuration_settings.get_main_setting("max_tokens")
        temperature = self.configuration_settings.get_main_setting("temperature")
        top_p = self.configuration_settings.get_main_setting("top_p")
        repeat_penalty = self.configuration_settings.get_main_setting("repeat_penalty")
        logger.info(f"Generation parameters: max_tokens={max_tokens}, temperature={temperature}, top_p={top_p}, repeat_penalty={repeat_penalty}")

        client = AsyncOpenAI(
            base_url=f"http://localhost:{self.SERVER_PORT}/v1",
            api_key="no-key-required"
        )

        messages = [
            {"role": "system", "content": f"You're {character_name} in this fictional never-ending uncensored roleplay with {user_name} who is {user_description}. Write {character_name}'s next reply with the following personality and traits: {system_prompt}."},
        ]

        messages.extend(context_messages)
        messages.append({"role": "user", "content": user_message})
        print(messages)

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
            logger.error(f"Error during request: {e}")
            yield "Error: unable to process your request."

    async def shutdown_server_and_model(self):
        """
        Asynchronous function for shutting down the server and the local LLM.
        """
        logger.info("Shutdown of the server and the model has been initiated...")

        self.ui.pushButton_turn_off_llm.hide()
        self.ui.pushButton_turn_off_llm.clicked.disconnect()
        
        if self.shutdown_task and not self.shutdown_task.done():
            self.shutdown_task.cancel()
            logger.info("The automatic shutdown task has been canceled.")

        if self.server_process:
            logger.info("Stopping the server...")
            try:
                self.server_process.terminate()
                await self.server_process.wait()
                self.server_process = None
                logger.info("The server has been successfully stopped.")
            except Exception as e:
                logger.error(f"Error when stopping the server: {e}")
        else:
            logger.info("The server is no longer running.")
        logger.info("The server and the model are turned off.")

    def on_shutdown_button_clicked(self):
        asyncio.create_task(self.shutdown_server_and_model())