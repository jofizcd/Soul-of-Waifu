import asyncio
import logging
import os

logger = logging.getLogger("Translator Module")

try:
    os.environ["translators_default_region"] = "EN"
    import translators as ts
    from translators.server import TranslatorError, TranslatorsServer
except Exception as e:
    logger.error(f"Error importing the online translator: {e}. Offline mode.")

    class TranslatorsServer:
        def __init__(self):
            raise RuntimeError("The online translator is not available offline.")

    class DummyTranslators:
        @staticmethod
        def translate_text(*args, **kwargs):
            return kwargs.get('query_text', '')

    ts = DummyTranslators()
    TranslatorError = RuntimeError


class Translator:
    def __init__(self):
        self._init_translators()

    def _init_translators(self):
        try:
            self.online_translator = TranslatorsServer()
        except Exception as e:
            logger.error(f"Translator initialization error: {e}")
            self.online_translator = None

    def translate(self, text: str, translator: str, language: str) -> str:
        try:
            return ts.translate_text(
                query_text=text,
                translator=translator,
                to_language=language
            )
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text

    async def translate_async(self, text: str, translator: str, language: str) -> str:
        try:
            return await asyncio.to_thread(
                ts.translate_text,
                query_text=text,
                translator=translator,
                to_language=language
            )
        except Exception as e:
            logger.error(f"Async translation error: {e}")
            return text
