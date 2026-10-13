"""Exercise real character-creator widgets and Soul Stage orchestration.

Soul Stage's source is loaded with only its GPU/provider imports replaced. All
parsers, world-state classes and orchestration methods run unchanged; HTTP is fake.
"""
import ast
import asyncio
import logging
import os
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6 import QtWidgets
from app.gui.character_ai_assistant import CharacterAIAssistantDialog
from app.utils.ai_clients.providers.chatgpt_provider import ChatGPTProviderError


def load_stage():
    path = Path(__file__).resolve().parents[1] / "app/utils/ai_clients/soul_stage_engine.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    tree.body = [node for node in tree.body if not (
        isinstance(node, ast.ImportFrom) and node.module in {
            "app.utils.ai_clients.ai_factory", "app.utils.ai_clients.prompt_engine"}
        or isinstance(node, ast.Import) and any(alias.name == "numpy" for alias in node.names))]
    module = ModuleType("_chatgpt_stage_test")
    module.__file__ = str(path)
    module.AIFactory = SimpleNamespace(get_provider=Mock())
    module.PromptEngine = object
    sys.modules[module.__name__] = module
    exec(compile(tree, str(path), "exec"), module.__dict__)
    return module


stage = load_stage()


class Stream:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    async def generate_stream(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        response = self.responses.pop(0)
        for item in response if isinstance(response, list) else [response]:
            if isinstance(item, BaseException):
                raise item
            yield item


class CharacterCreatorTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def make_dialog(self, stream):
        dialog = CharacterAIAssistantDialog(
            {}, Mock(), Mock(), SimpleNamespace(get_provider=Mock(return_value=stream)),
            default_provider="ChatGPT")
        self.addCleanup(dialog.close)
        return dialog

    async def test_character_creation_parses_completed_json_into_review(self):
        dialog = self.make_dialog(Stream('{"name": "Test Guide", "description": "A helpful guide."}'))
        await dialog._run_generation([{"role": "user", "content": "Create a guide"}], ["name", "description"], "full")
        self.assertEqual(dialog._review_widgets["name"].toPlainText(), "Test Guide")
        self.assertTrue(dialog.btn_generate.isEnabled())

    async def test_failed_character_generation_keeps_approved_fields(self):
        dialog = self.make_dialog(Stream('{"name":"Original"}', ['{"name":"Partial"}', ChatGPTProviderError("ChatGPT limit")]))
        await dialog._run_generation([], ["name"], "full")
        with self.assertLogs("Character AI Assistant", logging.ERROR):
            await dialog._run_generation([], ["name"], "full")
        self.assertEqual(dialog._review_widgets["name"].toPlainText(), "Original")
        self.assertEqual(dialog._generated_raw, '{"name":"Original"}')
        self.assertIn("ChatGPT limit", dialog.stream_output.toPlainText())
        self.assertTrue(dialog.btn_generate.isEnabled())

    async def test_regenerating_one_field_preserves_other_fields(self):
        dialog = self.make_dialog(Stream('{"name":"Original","description":"Keep me"}', '{"name":"Replacement"}'))
        await dialog._run_generation([], ["name", "description"], "full")
        await dialog._run_generation([], ["name"], "name")
        self.assertEqual(dialog._review_widgets["name"].toPlainText(), "Replacement")
        self.assertEqual(dialog._review_widgets["description"].toPlainText(), "Keep me")

    def test_character_creator_checks_active_plan_grant(self):
        dialog = self.make_dialog(Stream())
        for connected, enabled, expected in [(False, False, False), (True, False, False), (True, True, True)]:
            auth = SimpleNamespace(list_accounts=lambda: [{"active": True, "connected": connected, "plan_enabled": enabled}])
            with patch("app.utils.chatgpt_auth.get_chatgpt_auth", return_value=auth):
                self.assertEqual(dialog._check_provider_ready("ChatGPT", None)[0], expected)


class SoulStageTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = stage.SoulStageOrchestrator()
        self.engine.configuration_settings = SimpleNamespace(get_main_setting=lambda key: None)
        self.callbacks = {name: AsyncMock() for name in (
            "on_narrator_chunk", "on_narrator_done", "on_char_start", "on_char_chunk", "on_char_done",
            "on_npc_start", "on_npc_chunk", "on_npc_done", "on_turn_complete", "on_error")}

    async def run_turn(self, stream, party=None, character_stream=None):
        stage.AIFactory.get_provider = Mock(return_value=stream)
        await self.engine.run_turn("We open the door.", party or [], "ChatGPT", [], "Tester", "",
                                   character_stream or AsyncMock(), **self.callbacks)

    async def test_scene_planning_and_narration_complete(self):
        stream = Stream('{"next_actor":"PLAYER","narration_plan":"The room is bright."}', "The room is bright.")
        await self.run_turn(stream)
        self.callbacks["on_error"].assert_not_awaited()
        self.callbacks["on_narrator_done"].assert_awaited_once()
        self.callbacks["on_turn_complete"].assert_awaited_once()
        self.assertEqual(len(stream.calls), 2)
        self.assertEqual(stream.calls[0][1]["reasoning_effort"], "none")
        self.assertFalse(self.engine.is_running)

    async def test_plan_error_never_changes_world_or_starts_narration(self):
        stream = Stream(["{", ChatGPTProviderError("ChatGPT plan unavailable")])
        with self.assertLogs("Soul Stage", logging.ERROR):
            await self.run_turn(stream)
        self.assertEqual(self.engine.world_state.events, [])
        self.callbacks["on_narrator_chunk"].assert_not_awaited()
        self.callbacks["on_turn_complete"].assert_not_awaited()
        self.callbacks["on_error"].assert_awaited_once_with("ChatGPT plan unavailable")
        self.assertFalse(self.engine.is_running)

    async def test_narration_error_never_commits_partial_narration(self):
        stream = Stream('{"next_actor":"PLAYER","narration_plan":"A room."}', ["Partial", ChatGPTProviderError("Interrupted")])
        with self.assertLogs("Soul Stage", logging.ERROR):
            await self.run_turn(stream)
        self.callbacks["on_narrator_chunk"].assert_awaited()
        self.callbacks["on_narrator_done"].assert_not_awaited()
        self.callbacks["on_error"].assert_awaited_once_with("Interrupted")
        self.assertFalse(any(event.actor == "NARRATOR" for event in self.engine.world_state.events))

    async def test_party_memory_receives_chat_roles_and_same_provider(self):
        stream = Stream()
        stage.AIFactory.get_provider = Mock(return_value=stream)
        update = AsyncMock()
        self.engine.prompt_engine = SimpleNamespace(update_memory_after_response=update)
        await self.engine.sync_party_memory("ChatGPT", ["Alice", "Bob"], [
            {"role": "player", "content": "Hello"},
            {"role": "npc", "actor_name": "Guide", "content": "Welcome"}], "Tester")
        self.assertEqual(update.await_count, 2)
        arguments = update.await_args.kwargs
        self.assertIs(arguments["provider"], stream)
        self.assertEqual(arguments["new_messages"], [
            {"role": "user", "content": "Hello"}, {"role": "assistant", "content": "[Guide]: Welcome"}])

    async def test_npc_spawn_dialogue_and_routing_complete(self):
        stream = Stream(
            '{"next_actor":"Guide","spawns":[{"name":"Guide","archetype":"sage","personality":"Helpful"}]}',
            "A guide appears.", "Welcome to the library.", '{"next_actor":"PLAYER"}')
        await self.run_turn(stream)
        self.callbacks["on_error"].assert_not_awaited()
        self.callbacks["on_npc_done"].assert_awaited_once_with("Guide", "Welcome to the library.")
        self.assertEqual(self.engine.npc_registry.get("Guide").turn_count, 1)
        self.assertEqual(len(stream.calls), 4)

    async def test_party_character_receives_context_then_returns_control(self):
        received = []
        async def character_stream(*arguments):
            received.append(arguments)
            yield "I will explore the room."
        stream = Stream('{"next_actor":"Alice"}', "A room opens.", '{"next_actor":"PLAYER"}')
        await self.run_turn(stream, ["Alice"], character_stream)
        self.callbacks["on_error"].assert_not_awaited()
        self.callbacks["on_char_done"].assert_awaited_once_with("Alice", "I will explore the room.")
        self.assertEqual(received[0][0], "Alice")
        self.assertIn("A room opens.", received[0][2])

    async def test_failed_npc_response_does_not_commit_npc_turn(self):
        stream = Stream(
            '{"next_actor":"Guide","spawns":[{"name":"Guide"}]}', "A guide appears.",
            ["Partial NPC", ChatGPTProviderError("Interrupted")])
        with self.assertLogs("Soul Stage", logging.ERROR):
            await self.run_turn(stream)
        self.callbacks["on_npc_done"].assert_not_awaited()
        self.callbacks["on_error"].assert_awaited_once_with("Interrupted")
        self.assertEqual(self.engine.npc_registry.get("Guide").turn_count, 0)

    async def test_cancelled_scene_releases_running_state(self):
        stream = Stream('{"next_actor":"PLAYER"}', ["Partial", asyncio.CancelledError()])
        await self.run_turn(stream)
        self.callbacks["on_error"].assert_not_awaited()
        self.callbacks["on_narrator_done"].assert_not_awaited()
        self.callbacks["on_turn_complete"].assert_awaited_once()
        self.assertFalse(self.engine.is_running)
        self.assertIsNone(self.engine.current_task)


if __name__ == "__main__":
    unittest.main()
