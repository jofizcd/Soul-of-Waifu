import re
import translators as ts
from transformers import MarianMTModel, MarianTokenizer


class Translator:
    def __init__(self):
        self.tokenizer = None
        self.model = None

    def load_model(self, model_name):
        if self.tokenizer is None or self.model is None:
            self.tokenizer = MarianTokenizer.from_pretrained(self.model_name)
            self.model = MarianMTModel.from_pretrained(self.model_name)

    def translate(self, text, translator, language):
        text_translated = ts.translate_text(query_text=text, translator=translator, to_language=language)

        return text_translated
    
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