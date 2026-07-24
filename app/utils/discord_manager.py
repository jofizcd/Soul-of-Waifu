import asyncio
import logging
import discord
from discord.ext import commands

from app.configuration.configuration import ConfigurationAPI, ConfigurationCharacters

logger = logging.getLogger(__name__)

DISCORD_MAX_MESSAGE_LENGTH = 2000

def split_message(text: str, limit: int = DISCORD_MAX_MESSAGE_LENGTH) -> list[str]:
    return [text[i:i + limit] for i in range(0, len(text), limit)]

class DiscordBotManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.is_running = False
        self._bot_task = None
        self.token = ""
        self.chat_lock = asyncio.Lock()

        self.bot = None
        self._init_bot()

        self._config_cache: dict = {}
        self._config_dirty: bool = True

    def _init_bot(self):
        intents = discord.Intents.default()
        intents.message_content = True
        self.bot = commands.Bot(command_prefix="!", intents=intents)
        self._register_events()

    def invalidate_config_cache(self):
        self._config_dirty = True

    def _get_char_config(self, char_name: str) -> dict:
        if self._config_dirty:
            char_config_api = ConfigurationCharacters()
            all_chars = char_config_api.load_configuration()
            self._config_cache = all_chars.get("character_list", {})
            self._config_dirty = False
        return self._config_cache.get(char_name, {})

    def _register_events(self):
        @self.bot.event
        async def on_ready():
            logger.info(f"Discord bot logged in as {self.bot.user}")
            ui = getattr(self.main_window, "ui", None)
            toast = getattr(ui, "toast_notification", None) if ui else None
            if toast:
                toast.show_toast(f"Discord Bot online: {self.bot.user}", "app/gui/icons/discord.png")

        @self.bot.event
        async def on_message(message: discord.Message):
            try:
                if message.author == self.bot.user:
                    return

                await self.bot.process_commands(message)

                is_dm = isinstance(message.channel, discord.DMChannel)
                is_mentioned = self.bot.user and self.bot.user.mentioned_in(message)

                logger.debug(
                    f"on_message: author={message.author} channel={message.channel} "
                    f"is_dm={is_dm} is_mentioned={is_mentioned} content={message.content!r}"
                )

                if not is_dm and not is_mentioned:
                    logger.debug("on_message: ignored (not a DM and bot was not mentioned)")
                    return

                ctx = await self.bot.get_context(message)
                if ctx.valid:
                    logger.debug(f"on_message: ignored (matched a command: {message.content!r})")
                    return

                logger.info(f"on_message: dispatching to AI pipeline: {message.content!r}")
                await self.process_ai_response(message, message.content)

            except Exception as e:
                logger.error(f"Unhandled error in on_message: {e}", exc_info=True)
                try:
                    await message.channel.send(f"*Internal bot error: {e}*")
                except Exception as send_err:
                    logger.error(
                        f"Also failed to notify the channel about the error "
                        f"(likely missing permissions): {send_err}",
                        exc_info=True,
                    )

    async def process_ai_response(self, message: discord.Message, text_input: str):
        signals = self.main_window.interface_signals
        current_char = getattr(signals, "current_active_character", None)

        if not current_char:
            logger.warning(
                "process_ai_response: interface_signals.current_active_character is empty — "
                "open the character's chat in the app before messaging the bot on Discord."
            )
            await self._safe_reply(message, "*No character is currently loaded.*")
            return

        logger.debug(f"process_ai_response: current_active_character={current_char!r}")

        async with self.chat_lock:
            try:
                if text_input and self.bot.user:
                    text_input = text_input.replace(f"<@{self.bot.user.id}>", "").replace(f"<@!{self.bot.user.id}>", "").strip()

                char_info = self._get_char_config(current_char)
                conv_method = char_info.get("conversation_method", "Local LLM")
                logger.debug(f"process_ai_response: conversation_method={conv_method!r}")

                async with message.channel.typing():
                    await signals.handle_user_message(
                        character_name=current_char,
                        conversation_method=conv_method,
                        external_text=text_input,
                        discord_context=message
                    )

            except Exception as e:
                logger.error(f"Error passing message to Soul of Waifu: {e}", exc_info=True)
                await self._safe_reply(message, f"*Error: {str(e)}*")

    @staticmethod
    async def _safe_reply(message: discord.Message, content: str):
        try:
            await message.reply(content)
        except Exception as reply_err:
            logger.warning(f"message.reply() failed, falling back to channel.send(): {reply_err}")
            try:
                await message.channel.send(content)
            except Exception as send_err:
                logger.error(
                    f"channel.send() also failed — the bot likely lacks Send Messages "
                    f"permission in this channel: {send_err}",
                    exc_info=True,
                )

    def start_bot(self):
        if self.is_running:
            return

        config_api = ConfigurationAPI()
        self.token = config_api.get_token("DISCORD_BOT_TOKEN")

        if not self.token:
            logger.warning("No Discord token found.")
            return

        try:
            self._init_bot()
            
            loop = asyncio.get_running_loop()
            self.is_running = True
            self._bot_task = loop.create_task(self.bot.start(self.token))
            self._bot_task.add_done_callback(self._on_bot_task_done)
            logger.info("Discord Bot task started.")
        except Exception as e:
            self.is_running = False
            logger.error(f"Failed to start Discord Bot: {e}")

    def _on_bot_task_done(self, task: asyncio.Task):
        self.is_running = False
        if task.cancelled():
            logger.info("Discord Bot task was cancelled.")
        elif task.exception():
            logger.error(
                f"Discord Bot task crashed: {task.exception()}",
                exc_info=task.exception(),
            )

    async def stop_bot(self):
        if not self.is_running:
            return

        logger.info("Stopping Discord Bot...")
        if self.bot:
            await self.bot.close()

        if self._bot_task and not self._bot_task.done():
            self._bot_task.cancel()
            try:
                await self._bot_task
            except asyncio.CancelledError:
                pass

        self.is_running = False
        logger.info("Discord Bot stopped.")