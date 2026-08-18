import logging
import re

from app.utils.ai_clients.providers.openai_provider import OpenAIProvider

logger = logging.getLogger("Gemini Provider")

_NO_DISABLE_RE = re.compile(r"gemini-3|gemini.*-pro", re.IGNORECASE)


class GeminiProvider(OpenAIProvider):
    def __init__(self, api_key: str, model: str):
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
        super().__init__(api_key=api_key, model=model, base_url=base_url)

    def _is_reasoning_model(self) -> bool:
        return True

    def _apply_token_and_sampling_params(self, payload: dict, kwargs: dict, default_max_tokens: int):
        payload["max_tokens"] = kwargs.get("max_tokens", default_max_tokens)
        payload["temperature"] = kwargs.get("temperature", 0.7)
        payload["top_p"] = kwargs.get("top_p", 0.9)
        if kwargs.get("stop"):
            payload["stop"] = kwargs["stop"]

        reasoning_effort = kwargs.get("reasoning_effort")
        if reasoning_effort:
            if reasoning_effort == "none" and _NO_DISABLE_RE.search(self.model or ""):
                pass
            else:
                payload["reasoning_effort"] = reasoning_effort
        return payload
