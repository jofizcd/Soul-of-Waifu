import logging
from app.utils.ai_clients.providers.openai_provider import OpenAIProvider

logger = logging.getLogger("Gemini Provider")

class GeminiProvider(OpenAIProvider):
    def __init__(self, api_key: str, model: str):
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
        super().__init__(api_key=api_key, model=model, base_url=base_url)
