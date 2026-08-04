import logging
from app.utils.ai_clients.providers.openai_provider import OpenAIProvider

logger = logging.getLogger("Player2 Provider")

PLAYER2_GAME_ID = "019fa00a-5a28-72c5-b7c1-8eff39c20f8f"

class Player2Provider(OpenAIProvider):
    def __init__(self):
        super().__init__(
            api_key="no-key-required",
            model="default",
            base_url="http://127.0.0.1:4315/v1",
            extra_headers={"player2-game-key": PLAYER2_GAME_ID}
        )