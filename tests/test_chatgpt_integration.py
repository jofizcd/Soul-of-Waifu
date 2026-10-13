"""Exercise existing call-site bodies with isolated dependencies and settings."""

import ast
import asyncio
import importlib.util
import logging
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


def memory_caller():
    # Load the real method bodies without importing embedding/GUI dependencies.
    path = ROOT / "app/utils/ai_clients/prompt_engine.py"
    cls = next(node for node in ast.parse(path.read_text(encoding="utf-8")).body
               if isinstance(node, ast.ClassDef) and node.name == "PromptEngine")
    names = {"_get_soul_memory_max_tokens", "_memory_llm_call"}
    methods = [node for node in cls.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names]
    namespace = {"asyncio": asyncio, "logger": logging.getLogger("test.memory")}
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), "exec"), namespace)
    return type("MemoryCaller", (), {**{name: namespace[name] for name in names}, "SOUL_MEMORY_MIN_MAX_TOKENS": 4096})


class CallerTests(unittest.IsolatedAsyncioTestCase):
    async def test_memory_does_not_return_partial_stream_on_limit(self):
        async def stream(*args, **kwargs):
            yield "A long but incomplete memory that must never replace existing memory."
            raise RuntimeError("safe failure")

        caller = memory_caller()()
        caller.configuration_settings = SimpleNamespace(get_main_setting=lambda key: None)
        with self.assertLogs("test.memory", level="ERROR"):
            result = await caller._memory_llm_call(SimpleNamespace(generate_stream=stream), [])
        self.assertEqual(result, "")

    async def test_memory_buffers_success_and_passes_its_configured_reasoning(self):
        observed = []

        async def stream(messages, **kwargs):
            observed.append(kwargs)
            yield " Complete"
            yield " memory "

        caller = memory_caller()()
        caller.configuration_settings = SimpleNamespace(get_main_setting=lambda key: "none" if key == "soul_memory_reasoning_effort" else 250)
        self.assertEqual(await caller._memory_llm_call(SimpleNamespace(generate_stream=stream), []), "Complete memory")
        self.assertEqual(observed[0]["reasoning_effort"], "none")

    async def test_memory_cancellation_propagates(self):
        async def stream(*args, **kwargs):
            yield "partial"
            raise asyncio.CancelledError()

        caller = memory_caller()()
        caller.configuration_settings = SimpleNamespace(get_main_setting=lambda key: None)
        with self.assertRaises(asyncio.CancelledError):
            await caller._memory_llm_call(SimpleNamespace(generate_stream=stream), [])


class FactoryTests(unittest.TestCase):
    def test_all_existing_provider_routes_and_custom_endpoint_unchanged(self):
        path = ROOT / "app/utils/ai_clients/ai_factory.py"
        source = ast.parse(path.read_text(encoding="utf-8"))
        modules, constructors = {}, {}
        for node in source.body:
            if isinstance(node, ast.ImportFrom) and node.module and ".providers." in node.module:
                module = ModuleType(node.module)
                for alias in node.names:
                    constructor = Mock(name=alias.name)
                    setattr(module, alias.name, constructor)
                    constructors[alias.name] = constructor
                modules[node.module] = module
        config = ModuleType("app.configuration.configuration")
        settings = {"chatgpt_model": "account-model", "openai_model": "api-model"}
        config.ConfigurationSettings = lambda: SimpleNamespace(get_main_setting=settings.get)
        config.ConfigurationAPI = lambda: SimpleNamespace(get_token=lambda key: "https://custom.test" if key == "CUSTOM_ENDPOINT_URL" else "fake-key")
        modules[config.__name__] = config
        package = ModuleType("app.configuration")
        package.configuration = config
        modules[package.__name__] = package
        with patch.dict("sys.modules", modules):
            spec = importlib.util.spec_from_file_location("isolated_ai_factory", path)
            factory = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(factory)
            routes = {"ChatGPT": "ChatGPTProvider", "Open AI": "OpenAIProvider", "OpenRouter": "OpenRouterProvider",
                      "Mistral AI": "MistralProvider", "Anthropic": "AnthropicProvider", "Google Gemini": "GeminiProvider",
                      "DeepSeek": "DeepSeekProvider", "Grok": "GrokProvider", "Qwen": "QwenProvider",
                      "Z.AI": "ZAIProvider", "Player2": "Player2Provider", "Local LLM": "LocalProvider"}
            for route, name in routes.items():
                with self.subTest(route=route):
                    self.assertIs(factory.AIFactory.get_provider(route), constructors[name].return_value)
            self.assertEqual(constructors["ChatGPTProvider"].call_args.kwargs, {"model": "account-model"})
            self.assertEqual(constructors["OpenAIProvider"].call_args.kwargs,
                             {"api_key": "fake-key", "model": "api-model", "base_url": "https://custom.test/v1"})


if __name__ == "__main__":
    unittest.main()
