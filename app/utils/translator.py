import re
import logging

from transformers import MarianMTModel, MarianTokenizer

logger = logging.getLogger("Translator Module")

try:
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
        self.tokenizer = None
        self.model = None
        self._init_translators()
    
    def _init_translators(self):
        try:
            self.online_translator = TranslatorsServer()
        except Exception as e:
            logger.error(f"Translator initialization error: {e}")
            self.online_translator = None

    def load_model(self, model_name):
        if self.tokenizer is None or self.model is None:
            self.tokenizer = MarianTokenizer.from_pretrained(self.model_name)
            self.model = MarianMTModel.from_pretrained(self.model_name)

    def translate(self, text, translator, language):
        try:
            return ts.translate_text(
                query_text=text, 
                translator=translator, 
                to_language=language
            )
        except Exception as e:
            logger.error(f"Unknown translation error: {e}")
        
    def translate_local(self, text, source_lang, target_lang, max_length=512):
        self.model_name = f"Helsinki-NLP/opus-mt-{source_lang}-{target_lang}"
        self.load_model(self.model_name)

        chunks = self._split_text_into_chunks(text, max_length)

        translated_text = ""
        for chunk in chunks:
            inputs = self.tokenizer(chunk, return_tensors="pt", padding=True, truncation=True)
            translated = self.model.generate(**inputs)
            translated_chunk = self.tokenizer.decode(translated[0], skip_special_tokens=True)
            translated_text += translated_chunk + " "

        return translated_text.strip()

    def _split_text_into_chunks(self, text, max_length):
        sentences = re.split(r'(?<=[.!?]) +', text)

        chunks = []
        current_chunk = ""
        current_length = 0

        for sentence in sentences:
            sentence_tokens = self.tokenizer.tokenize(sentence)
            sentence_length = len(sentence_tokens)

            if current_length + sentence_length > max_length:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                    current_length = 0

                if sentence_length > max_length:
                    sub_chunks = self._split_long_sentence(sentence, max_length)
                    chunks.extend(sub_chunks)
                else:
                    current_chunk = sentence
                    current_length = sentence_length
            else:
                current_chunk += " " + sentence if current_chunk else sentence
                current_length += sentence_length

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _split_long_sentence(self, sentence, max_length):
        tokens = self.tokenizer.tokenize(sentence)

        chunks = []
        current_chunk = []
        current_length = 0

        for token in tokens:
            current_chunk.append(token)
            current_length += 1

            if current_length >= max_length:
                chunks.append(self.tokenizer.convert_tokens_to_string(current_chunk))
                current_chunk = []
                current_length = 0

        if current_chunk:
            chunks.append(self.tokenizer.convert_tokens_to_string(current_chunk))

        return chunks
