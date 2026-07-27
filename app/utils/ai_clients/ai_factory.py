import logging
from app.configuration import configuration
from app.utils.ai_clients.providers.openai_provider import OpenAIProvider
from app.utils.ai_clients.providers.openrouter_provider import OpenRouterProvider
from app.utils.ai_clients.providers.mistral_provider import MistralProvider
from app.utils.ai_clients.providers.local_provider import LocalProvider
from app.utils.ai_clients.providers.anthropic_provider import AnthropicProvider
from app.utils.ai_clients.providers.gemini_provider import GeminiProvider
from app.utils.ai_clients.providers.deepseek_provider import DeepSeekProvider
from app.utils.ai_clients.providers.grok_provider import GrokProvider
from app.utils.ai_clients.providers.qwen_provider import QwenProvider
from app.utils.ai_clients.providers.zai_provider import ZAIProvider

logger = logging.getLogger("AI Factory")

class AIFactory:
    @staticmethod
    def get_provider(conversation_method: str, model_override: str = None):
        """
        Factory method to instantiate the appropriate AI provider.
        """
        config_settings = configuration.ConfigurationSettings()
        config_api = configuration.ConfigurationAPI()

        if conversation_method == "Open AI":
            api_key = config_api.get_token("OPEN_AI_API_TOKEN")
            model = model_override or config_settings.get_main_setting("openai_model") or "gpt-4o-mini"
            base_url = config_api.get_token("CUSTOM_ENDPOINT_URL")
            if base_url and base_url.strip():
                base_url = base_url.strip().rstrip('/')
                if not base_url.endswith('/v1'):
                    base_url = f"{base_url}/v1"
            else:
                base_url = "https://api.openai.com/v1"
            
            return OpenAIProvider(api_key=api_key, model=model, base_url=base_url)

        elif conversation_method == "OpenRouter":
            api_key = config_api.get_token("OPENROUTER_API_TOKEN")
            model = model_override or config_settings.get_main_setting("openrouter_model")
            base_url = "https://openrouter.ai/api/v1"

            return OpenRouterProvider(api_key=api_key, model=model, base_url=base_url)

        elif conversation_method == "Mistral AI":
            api_key = config_api.get_token("MISTRAL_AI_API_TOKEN")
            model = model_override or config_settings.get_main_setting("mistral_model_endpoint") or "mistral-small-latest"
            return MistralProvider(api_key=api_key, model=model)

        elif conversation_method == "Anthropic":
            api_key = config_api.get_token("ANTHROPIC_API_TOKEN")
            model = model_override or config_settings.get_main_setting("anthropic_model") or "claude-sonnet-4-6"
            return AnthropicProvider(api_key=api_key, model=model)

        elif conversation_method == "Google Gemini":
            api_key = config_api.get_token("GEMINI_API_TOKEN")
            model = model_override or config_settings.get_main_setting("gemini_model") or "gemini-3.5-flash"
            return GeminiProvider(api_key=api_key, model=model)

        elif conversation_method == "DeepSeek":
            api_key = config_api.get_token("DEEPSEEK_API_TOKEN")
            model = model_override or config_settings.get_main_setting("deepseek_model") or "deepseek-v4-flash"
            return DeepSeekProvider(api_key=api_key, model=model)

        elif conversation_method == "Grok":
            api_key = config_api.get_token("GROK_API_TOKEN")
            model = model_override or config_settings.get_main_setting("grok_model") or "grok-4.3"
            return GrokProvider(api_key=api_key, model=model)

        elif conversation_method == "Qwen":
            api_key = config_api.get_token("QWEN_API_TOKEN")
            model = model_override or config_settings.get_main_setting("qwen_model") or "qwen3.5-flash"
            return QwenProvider(api_key=api_key, model=model)

        elif conversation_method == "Z.AI":
            api_key = config_api.get_token("ZAI_API_TOKEN")
            model = model_override or config_settings.get_main_setting("zai_model") or "glm-4.7"
            return ZAIProvider(api_key=api_key, model=model)

        elif conversation_method == "Local LLM":
            advanced_enabled = config_settings.get_main_setting("adv_sampling")
            advanced_params = {}
            if advanced_enabled:
                advanced_params = {
                    "min_p": config_settings.get_main_setting("min_p") or 0.05,
                    "xtc_probability": config_settings.get_main_setting("xtc_probability") or 0.0,
                    "xtc_threshold": config_settings.get_main_setting("xtc_threshold") or 0.1,
                    "dry_multiplier": config_settings.get_main_setting("dry_multiplier") or 0.0,
                    "dry_base": config_settings.get_main_setting("dry_base") or 1.75,
                    "dry_allowed_length": config_settings.get_main_setting("dry_allowed_length") or 2
                }
                
                dyn_temp_min = config_settings.get_main_setting("dyn_temp_min")
                dyn_temp_max = config_settings.get_main_setting("dyn_temp_max")
                if dyn_temp_min is not None and dyn_temp_max is not None:
                    dyn_range = (float(dyn_temp_max) - float(dyn_temp_min)) / 2.0
                    if dyn_range > 0:
                        advanced_params["dynatemp_range"] = dyn_range

            return LocalProvider(port=48596, advanced_params=advanced_params)

        else:
            logger.error(f"Unknown conversation method requested: {conversation_method}")
            return None
