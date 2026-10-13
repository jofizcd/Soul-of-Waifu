"""Execute complete GUI handlers against Qt widgets and an in-memory chat store.

Methods are loaded without importing the unrelated GPU/voice application startup.
No real account, browser, chat files, or network is accessed.
"""
import ast
import asyncio
import copy
import logging
import inspect
import json
import textwrap
import time
import os
from pathlib import Path
import re
from types import MethodType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock
import uuid

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6 import QtCore, QtWidgets
from app.utils.chatgpt_auth import ChatGPTAuthError
from app.utils.ai_clients.providers.chatgpt_provider import ChatGPTProviderError
from app.utils.ai_clients.tools import normalize_tool_call


METHODS = {"handle_user_message", "regenerate_message", "continue_dialog", "run_tool_loop",
           "_generate_chat_stream", "_stream_chatgpt_with_tools", "_restore_chatgpt_chat",
           "stop_generation", "update_api_token"}


def load_handlers(factory):
    path = Path(__file__).parents[1] / "app/gui/interface_signals.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    owner = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "InterfaceSignals")
    methods = [n for n in owner.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in METHODS]
    scope = dict(asyncio=asyncio, os=os, re=re, uuid=uuid, QtCore=QtCore,
                 json=json, time=time, normalize_tool_call=normalize_tool_call,
                 QApplication=QtWidgets.QApplication, AIFactory=factory,
                 logger=Mock(spec=logging.Logger), ChatGPTAuthError=ChatGPTAuthError,
                 ChatGPTProviderError=ChatGPTProviderError,
                 TypingIndicatorWidget=lambda *args: QtWidgets.QLabel("Working"),
                 extract_reasoning=lambda text: (text, ""),
                 strip_partial_state_tag=lambda text: text,
                 extract_state_update=lambda text, **kwargs: (text, {}))
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), "exec"), scope)
    return scope


class ChatStore:
    def __init__(self, provider="ChatGPT"):
        self.saved = []
        self.regenerated = []
        self.deleted = []
        messages = {}
        for seq, (key, user, text) in enumerate([
                ("u1", True, "Question"), ("a1", False, "Original answer"),
                ("u2", True, "Later question"), ("a2", False, "Later answer")]):
            messages[key] = dict(message_id=key, is_user=user, text=text, sequence_number=seq)
        self.data = {"character_list": {"Character": {"conversation_method": provider,
                     "current_chat": "default", "chats": {"default": {"chat_content": messages}}}}}

    @property
    def messages(self):
        return self.data["character_list"]["Character"]["chats"]["default"]["chat_content"]

    def load_configuration(self):
        return copy.deepcopy(self.data)

    def add_message_to_config(self, character, author, is_user, text, message_id):
        self.saved.append((is_user, text))

    def delete_chat_messages(self, character, ids):
        self.deleted.extend(ids)
        for key in ids:
            self.messages.pop(key, None)

    def regenerate_message_in_config(self, character, key, text):
        self.regenerated.append((key, text))
        self.messages[key]["text"] = text


class Provider:
    def __init__(self, chunks=("Hello", " world"), error=None):
        self.chunks, self.error = chunks, error
        self.calls = 0
        self.closed = False
        self.generate = AsyncMock(side_effect=error or ChatGPTAuthError("Sign in again"))

    async def generate_stream(self, messages, **kwargs):
        self.calls += 1
        try:
            for chunk in self.chunks:
                yield chunk
            if self.error:
                raise self.error
        finally:
            self.closed = True

    async def generate_tool_stream(self, messages, tools=None, **kwargs):
        result = await self.generate(messages, tools=tools, **kwargs)
        if result.get("content"):
            yield {"type": "text_delta", "text": result["content"]}
        yield {"type": "completed", "result": result}


class GuiFlowTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.provider = Provider()
        self.factory = Mock()
        self.factory.get_provider.side_effect = lambda name: self.provider
        self.scope = load_handlers(self.factory)
        self.store = ChatStore()
        self.editor = QtWidgets.QTextEdit()
        self.editor.setPlainText("New question")
        self.send, self.stop = QtWidgets.QPushButton(), QtWidgets.QPushButton()
        self.send.show()
        self.stop.hide()
        self.container = QtWidgets.QWidget()
        self.layout = QtWidgets.QVBoxLayout(self.container)
        self.scroll = QtWidgets.QScrollArea()
        self.owner = SimpleNamespace(
            configuration_characters=self.store,
            configuration_settings=SimpleNamespace(get_main_setting=lambda k: None,
                                                   get_user_data=lambda k: {}),
            ui=SimpleNamespace(textEdit_write_user_message=self.editor,
                               pushButton_send_message=self.send, pushButton_stop_generation=self.stop,
                               scrollArea_chat=self.scroll),
            textEdit_write_user_message=self.editor, pending_attachments=[],
            OPENAI_STYLE_VISION_PROVIDERS={"ChatGPT"}, ANTHROPIC_STYLE_VISION_PROVIDERS=set(),
            chat_tts_worker=None, chat_container=self.layout, _pending_tts_segments={},
            markdown_to_html=lambda t: t, apply_macros=lambda t, *args: t,
            get_chat_appearance=lambda: {}, tools_enabled=False,
            tool_registry=SimpleNamespace(has_tools=lambda: True, get_schemas=lambda: []),
            MAX_TOOL_LOOP_ITERATIONS=4, _get_gen_kwargs=lambda method: {},
            _build_rich_user_text_for_context=lambda character, message: message["text"],
            _wire_thinking_toggle=Mock(), _show_chatgpt_error=Mock(),
            _refresh_attachment_preview_bar=Mock(), first_render_messages=AsyncMock(),
            render_messages=AsyncMock(), translations={},
            prompt_engine=SimpleNamespace(build_system_prompt_blocks=lambda *args, **kw: ([{"role": "user", "content": "Hi"}], []),
                                         update_memory_after_response=AsyncMock()),
            messages={key: {"label": QtWidgets.QLabel(v["text"]), "frame": QtWidgets.QWidget()}
                      for key, v in self.store.messages.items()},
            message_order=list(self.store.messages))
        for name in METHODS:
            setattr(self.owner, name, MethodType(self.scope[name], self.owner))
        async def add_message(character, text, is_user, message_id=None, **kwargs):
            label = QtWidgets.QLabel(text)
            self.layout.addWidget(label)
            return {"label": label, "message_id": message_id or str(uuid.uuid4())}
        self.owner.add_message = add_message
        self.owner.clear_pending_attachments = lambda: setattr(self.owner, "pending_attachments", [])

    def tearDown(self):
        self.editor.close()
        self.send.close()
        self.stop.close()
        self.container.close()
        self.scroll.close()
        for message in self.owner.messages.values():
            message["label"].close()
            message["frame"].close()
        self.app.processEvents()

    async def chat(self):
        await self.owner.handle_user_message("Character", "ChatGPT")

    def assert_buttons_restored(self):
        self.assertTrue(self.stop.isHidden())
        self.assertFalse(self.send.isHidden())

    async def test_success_saves_user_and_answer_and_restores_buttons(self):
        await self.chat()
        self.assertEqual(self.store.saved, [(True, "New question"), (False, "Hello world")])
        self.assertTrue(self.provider.closed)
        self.owner.prompt_engine.update_memory_after_response.assert_awaited_once()
        self.assert_buttons_restored()
        self.scope["logger"].error.assert_not_called()

    async def test_chatgpt_repeated_deltas_are_not_treated_as_cumulative_text(self):
        self.provider.chunks = ("ha", "ha")
        await self.chat()
        self.assertEqual(self.store.saved[-1], (False, "haha"))

    async def test_first_chunk_atomically_replaces_typing_with_initialized_answer(self):
        entered, first_ready, received, finish = (asyncio.Event() for _ in range(4))
        indicators, answers, transitions = [], [], []
        def typing_widget(*args):
            label = QtWidgets.QLabel("Working")
            indicators.append(label)
            return label
        self.scope["TypingIndicatorWidget"] = typing_widget
        original_add = self.owner.add_message
        async def add_message(character, text, is_user, message_id=None, **kwargs):
            if not is_user:
                # Observe before constructing the replacement, while the handler
                # would previously have removed its only visible assistant widget.
                indicator = indicators[-1]
                transitions.append({"text": text,
                                    "deferred": kwargs.get("defer_layout", False),
                                    "indicator_attached": self.layout.indexOf(indicator) >= 0,
                                    "indicator_hidden": indicator.isHidden()})
            result = await original_add(character, text, is_user, message_id, **kwargs)
            if not is_user:
                answers.append(result["label"])
            return result
        self.owner.add_message = add_message
        async def stream(*args, **kwargs):
            entered.set()
            await first_ready.wait()
            yield "Character: First words"
            received.set()
            await finish.wait()
            yield " and the rest."
        self.provider.generate_stream = stream
        self.container.show()
        task = asyncio.create_task(self.chat())
        try:
            await asyncio.wait_for(entered.wait(), 3)
            self.app.processEvents()
            self.assertEqual(len(indicators), 1)
            self.assertTrue(indicators[0].isVisible())
            self.assertEqual(answers, [])
            first_ready.set()
            await asyncio.wait_for(received.wait(), 3)
            self.app.processEvents()
            self.assertEqual(transitions, [{"text": "First words", "deferred": True,
                                           "indicator_attached": True, "indicator_hidden": False}])
            self.assertEqual(len(answers), 1)
            self.assertTrue(answers[0].isVisible())
            self.assertEqual(answers[0].text(), "First words")
            self.assertEqual(self.store.saved, [])
            self.assertNotIn("Working", [self.layout.itemAt(i).widget().text()
                                          for i in range(self.layout.count())
                                          if isinstance(self.layout.itemAt(i).widget(), QtWidgets.QLabel)])
            finish.set()
            await task
        finally:
            first_ready.set()
            finish.set()
            if not task.done():
                task.cancel()
                await task
        self.assertEqual(self.store.saved[-1], (False, "First words and the rest."))
        self.assert_buttons_restored()

    async def test_typed_failure_after_partial_output_saves_nothing_and_restores_input(self):
        self.provider.error = ChatGPTProviderError("Usage limit reached")
        await self.chat()
        self.assertEqual(self.store.saved, [])
        self.assertEqual(self.editor.toPlainText(), "New question")
        self.owner.first_render_messages.assert_awaited_once()
        self.owner.prompt_engine.update_memory_after_response.assert_not_called()
        self.owner._show_chatgpt_error.assert_called_once()
        self.assertTrue(self.provider.closed)
        self.assert_buttons_restored()

    async def test_auth_failure_in_tools_does_not_send_second_request(self):
        self.owner.tools_enabled = True
        await self.chat()
        self.assertEqual(self.provider.calls, 0)
        self.provider.generate.assert_awaited_once()
        self.assertEqual(self.store.saved, [])
        self.assert_buttons_restored()

    def enable_tool_answers(self, results):
        self.owner.tools_enabled = True
        self.provider.generate = AsyncMock(side_effect=results)
        self.owner._show_tool_usage_indicator = Mock(return_value=None)
        self.owner._remove_tool_usage_indicator = Mock()
        self.owner.tool_registry.execute = AsyncMock(return_value={"result": "42"})

    @staticmethod
    def tool_call(call_id="call_1"):
        return {"id": call_id, "type": "function",
                "function": {"name": "calculator", "arguments": '{"expression":"6*7"}'}}

    async def test_tool_stream_displays_text_before_terminal_and_executes_completed_calls_only(self):
        self.enable_tool_answers([])
        waiting, release = asyncio.Event(), asyncio.Event()
        requests, closed = [], []
        async def events(messages, **kwargs):
            requests.append(copy.deepcopy(messages))
            round_index = len(requests)
            try:
                if round_index == 1:
                    yield {"type": "text_delta", "text": "Checking"}
                    # Only the terminal result is allowed to authorize execution.
                    yield {"type": "tool_call_delta", "tool_calls": [self.tool_call()]}
                    waiting.set()
                    await release.wait()
                    yield {"type": "completed", "result": {"content": "Checking", "tool_calls": [
                        self.tool_call("call_1"), self.tool_call("call_2")]}}
                else:
                    yield {"type": "text_delta", "text": "Forty"}
                    yield {"type": "text_delta", "text": " two"}
                    yield {"type": "completed", "result": {"content": "Forty two", "tool_calls": None}}
            finally:
                closed.append(round_index)
        self.provider.generate_tool_stream = events
        task = asyncio.create_task(self.chat())
        await asyncio.wait_for(waiting.wait(), 3)
        self.assertIn("Checking", [w.text() for w in self.container.findChildren(QtWidgets.QLabel)])
        self.assertEqual(self.store.saved, [])
        self.owner.tool_registry.execute.assert_not_awaited()
        release.set()
        await task
        self.assertEqual(self.store.saved[-1], (False, "Checking\n\nForty two"))
        self.assertEqual(len(requests), 2)
        self.assertEqual(self.owner.tool_registry.execute.await_count, 2)
        self.assertEqual(requests[1][-3]["content"], "Checking")
        self.assertEqual([m["tool_call_id"] for m in requests[1][-2:]], ["call_1", "call_2"])
        self.assertEqual(closed, [1, 2])
        self.assertEqual(self.provider.calls, 0)
        self.assert_buttons_restored()

    async def test_tool_stream_failure_after_visible_delta_rolls_back_without_execution(self):
        self.enable_tool_answers([])
        closed = []
        async def events(*args, **kwargs):
            try:
                yield {"type": "text_delta", "text": "Partial"}
                yield {"type": "tool_call_delta", "tool_calls": [self.tool_call()]}
                raise ChatGPTProviderError("Interrupted")
            finally:
                closed.append(True)
        self.provider.generate_tool_stream = events
        await self.chat()
        self.assertEqual(self.store.saved, [])
        self.assertEqual(self.editor.toPlainText(), "New question")
        self.owner.tool_registry.execute.assert_not_awaited()
        self.owner.first_render_messages.assert_awaited_once()
        self.assertEqual(closed, [True])
        self.assertEqual(self.provider.calls, 0)
        self.assert_buttons_restored()

    async def test_tool_stream_missing_terminal_is_not_saved_as_success(self):
        self.enable_tool_answers([])
        async def events(*args, **kwargs):
            yield {"type": "text_delta", "text": "Partial"}
        self.provider.generate_tool_stream = events
        await self.chat()
        self.assertEqual(self.store.saved, [])
        self.owner.tool_registry.execute.assert_not_awaited()
        self.owner._show_chatgpt_error.assert_called_once()
        self.assert_buttons_restored()

    async def test_stop_delivered_after_completed_response_prevents_tool_execution(self):
        self.enable_tool_answers([{"content": "Checking", "tool_calls": [self.tool_call()]}])
        self.owner._show_tool_usage_indicator.side_effect = lambda *args: self.owner.stop_generation()
        await self.chat()
        self.owner.tool_registry.execute.assert_not_awaited()
        self.assertEqual(self.store.saved, [])
        self.assertEqual(self.editor.toPlainText(), "New question")
        self.owner._remove_tool_usage_indicator.assert_called_once()
        self.owner._show_chatgpt_error.assert_not_called()
        self.assert_buttons_restored()

    async def test_stop_after_completed_tool_cancels_next_stream_and_warns(self):
        self.enable_tool_answers([])
        waiting = asyncio.Event()
        closed = []
        requests = []
        async def events(messages, **kwargs):
            requests.append(copy.deepcopy(messages))
            try:
                if len(requests) == 1:
                    yield {"type": "completed", "result": {"content": None, "tool_calls": [self.tool_call()]}}
                else:
                    yield {"type": "text_delta", "text": "Partial answer"}
                    waiting.set()
                    await asyncio.Event().wait()
            finally:
                closed.append(True)
        self.provider.generate_tool_stream = events
        task = asyncio.create_task(self.chat())
        await asyncio.wait_for(waiting.wait(), 3)
        self.owner.stop_generation()
        await task
        self.assertEqual(self.store.saved, [])
        self.owner.tool_registry.execute.assert_awaited_once()
        self.owner._show_chatgpt_error.assert_called_once()
        self.assertEqual(len(closed), 2)
        self.assertEqual(self.provider.calls, 0)
        self.assert_buttons_restored()

    async def test_regeneration_streams_tool_answer_before_terminal(self):
        self.enable_tool_answers([])
        waiting, release = asyncio.Event(), asyncio.Event()
        async def events(*args, **kwargs):
            yield {"type": "text_delta", "text": "Replacement"}
            waiting.set()
            await release.wait()
            yield {"type": "completed", "result": {"content": "Replacement", "tool_calls": None}}
        self.provider.generate_tool_stream = events
        task = asyncio.create_task(self.owner.regenerate_message("ChatGPT", "Character", "a1"))
        await asyncio.wait_for(waiting.wait(), 3)
        self.assertEqual(self.owner.messages["a1"]["label"].text(), "Replacement")
        self.assertEqual(self.store.regenerated, [])
        release.set()
        await task
        self.assertEqual(self.store.regenerated, [("a1", "Replacement")])
        self.assertEqual(self.provider.calls, 0)
        self.assert_buttons_restored()

    async def test_tools_enabled_reuses_answer_without_second_generation(self):
        self.enable_tool_answers([{"content": "Already answered", "tool_calls": None}])
        self.owner._get_gen_kwargs = lambda method: {"reasoning_effort": "low"}
        await self.chat()
        self.assertEqual(self.store.saved, [(True, "New question"), (False, "Already answered")])
        self.provider.generate.assert_awaited_once()
        self.assertEqual(self.provider.generate.await_args.kwargs["reasoning_effort"], "low")
        self.assertEqual(self.provider.calls, 0)
        self.owner.tool_registry.execute.assert_not_awaited()
        self.assert_buttons_restored()

    async def test_tools_enabled_reuses_answer_after_tool_result(self):
        self.enable_tool_answers([
            {"content": None, "tool_calls": [{"id": "call_1", "type": "function",
             "function": {"name": "calculator", "arguments": '{"expression":"6*7"}'}}]},
            {"content": "The answer is 42", "tool_calls": None},
        ])
        await self.chat()
        self.assertEqual(self.store.saved[-1], (False, "The answer is 42"))
        self.assertEqual(self.provider.generate.await_count, 2)
        self.assertEqual(self.provider.calls, 0)
        self.owner.tool_registry.execute.assert_awaited_once()
        request = self.provider.generate.await_args.args[0]
        self.assertEqual(request[-1], {"role": "tool", "tool_call_id": "call_1",
                                       "name": "calculator", "content": "42"})
        self.assert_buttons_restored()

    async def test_tool_iteration_limit_still_requests_final_answer_with_results(self):
        self.owner.MAX_TOOL_LOOP_ITERATIONS = 1
        self.enable_tool_answers([
            {"content": None, "tool_calls": [{"id": "call_1", "type": "function",
             "function": {"name": "calculator", "arguments": '{"expression":"6*7"}'}}]},
        ])
        captured = []
        original_stream = self.provider.generate_stream
        async def stream(messages, **kwargs):
            captured.extend(messages)
            async for chunk in original_stream(messages, **kwargs):
                yield chunk
        self.provider.generate_stream = stream
        await self.chat()
        self.assertEqual(self.store.saved[-1], (False, "Hello world"))
        self.provider.generate.assert_awaited_once()
        self.assertEqual(self.provider.calls, 1)
        self.assertEqual(captured[-1]["role"], "tool")
        self.assertEqual(captured[-1]["content"], "42")
        self.assert_buttons_restored()

    async def test_failure_after_tool_result_does_not_retry_or_save_answer(self):
        self.enable_tool_answers([
            {"content": None, "tool_calls": [{"id": "call_1", "type": "function",
             "function": {"name": "calculator", "arguments": '{"expression":"6*7"}'}}]},
            ChatGPTProviderError("Connection interrupted"),
        ])
        await self.chat()
        self.assertEqual(self.store.saved, [])
        self.assertEqual(self.editor.toPlainText(), "New question")
        self.assertEqual(self.provider.generate.await_count, 2)
        self.assertEqual(self.provider.calls, 0)
        self.owner.tool_registry.execute.assert_awaited_once()
        self.owner._show_chatgpt_error.assert_called_once()
        self.assert_buttons_restored()

    async def test_regeneration_reuses_tool_pass_answer(self):
        self.enable_tool_answers([{"content": "Replacement", "tool_calls": None}])
        await self.owner.regenerate_message("ChatGPT", "Character", "a1")
        self.assertEqual(self.store.regenerated, [("a1", "Replacement")])
        self.assertEqual(list(self.store.messages), ["u1", "a1"])
        self.provider.generate.assert_awaited_once()
        self.assertEqual(self.provider.calls, 0)
        self.assert_buttons_restored()

    async def test_tools_enabled_other_provider_keeps_streaming_pass(self):
        self.store.data["character_list"]["Character"]["conversation_method"] = "Open AI"
        self.enable_tool_answers([{"content": "Planning answer", "tool_calls": None}])
        await self.chat()
        self.assertEqual(self.store.saved[-1], (False, "Hello world"))
        self.provider.generate.assert_awaited_once()
        self.assertEqual(self.provider.generate.await_args.kwargs,
                         {"tools": [], "temperature": 0.1, "max_tokens": 600})
        self.assertEqual(self.provider.calls, 1)
        self.assert_buttons_restored()

    async def test_stop_during_tool_pass_preserves_history_and_sends_no_second_request(self):
        self.owner.tools_enabled = True
        entered = asyncio.Event()
        async def waiting_response(*args, **kwargs):
            entered.set()
            await asyncio.Event().wait()
        self.provider.generate = AsyncMock(side_effect=waiting_response)
        task = asyncio.create_task(self.chat())
        await entered.wait()
        self.owner.stop_generation()
        await task
        self.assertEqual(self.store.saved, [])
        self.assertEqual(self.editor.toPlainText(), "New question")
        self.assertEqual(self.provider.calls, 0)
        self.owner.prompt_engine.update_memory_after_response.assert_not_called()
        self.assert_buttons_restored()

    async def test_cancel_after_partial_output_does_not_save_or_run_memory(self):
        self.provider.error = asyncio.CancelledError()
        await self.chat()
        self.assertEqual(self.store.saved, [])
        self.assertEqual(self.editor.toPlainText(), "New question")
        self.owner._show_chatgpt_error.assert_not_called()
        self.owner.prompt_engine.update_memory_after_response.assert_not_called()
        self.assertTrue(self.provider.closed)
        self.assert_buttons_restored()

    async def test_stop_interrupts_waiting_request_and_hides_send_until_rollback_finishes(self):
        entered = asyncio.Event()
        rendering = asyncio.Event()
        release_render = asyncio.Event()
        async def waiting_stream(*args, **kwargs):
            entered.set()
            await asyncio.Event().wait()
            yield "never"
        self.provider.generate_stream = waiting_stream
        async def render(*args):
            rendering.set()
            await release_render.wait()
        self.owner.first_render_messages = render
        task = asyncio.create_task(self.chat())
        await entered.wait()
        self.owner.stop_generation()
        self.assertTrue(self.send.isHidden())
        await rendering.wait()
        self.assertTrue(self.send.isHidden())
        release_render.set()
        await task
        self.assertEqual(self.store.saved, [])
        self.assertEqual(self.editor.toPlainText(), "New question")
        self.assert_buttons_restored()

    async def test_stop_after_stream_completion_cannot_interrupt_two_message_commit(self):
        loop = asyncio.get_running_loop()
        original_save = self.store.add_message_to_config
        observed = []
        def save(*args):
            if args[2]:
                observed.append(self.owner._chatgpt_commit_in_progress)
                loop.call_soon_threadsafe(self.owner.stop_generation)
            original_save(*args)
        self.store.add_message_to_config = save
        await self.chat()
        self.assertEqual(observed, [True])
        self.assertEqual(self.store.saved, [(True, "New question"), (False, "Hello world")])
        self.assertFalse(self.owner.abort_generation)
        self.assertFalse(self.owner._chatgpt_commit_in_progress)
        self.assert_buttons_restored()

    async def test_failure_preserves_a_new_draft_already_typed_in_composer(self):
        async def stream(*args, **kwargs):
            self.editor.setPlainText("Already typing next message")
            raise ChatGPTAuthError("Sign in again")
            yield "never"
        self.provider.generate_stream = stream
        await self.chat()
        self.assertEqual(self.editor.toPlainText(), "Already typing next message")
        self.assertEqual(self.store.saved, [])

    async def test_regeneration_failure_preserves_all_future_messages(self):
        before = copy.deepcopy(self.store.data)
        self.provider.error = ChatGPTProviderError("Usage limit reached")
        await self.owner.regenerate_message("ChatGPT", "Character", "a1")
        self.assertEqual(self.store.data, before)
        self.assertEqual(self.store.regenerated, [])
        self.owner.first_render_messages.assert_awaited_once()
        self.assert_buttons_restored()

    async def test_regeneration_cancel_preserves_original_and_future_messages(self):
        before = copy.deepcopy(self.store.data)
        self.provider.error = asyncio.CancelledError()
        await self.owner.regenerate_message("ChatGPT", "Character", "a1")
        self.assertEqual(self.store.data, before)
        self.assertTrue(self.provider.closed)
        self.owner._show_chatgpt_error.assert_not_called()
        self.assert_buttons_restored()

    async def test_regeneration_success_replaces_answer_and_truncates_following_messages(self):
        await self.owner.regenerate_message("ChatGPT", "Character", "a1")
        self.assertEqual(self.store.regenerated, [("a1", "Hello world")])
        self.assertEqual(list(self.store.messages), ["u1", "a1"])
        self.assert_buttons_restored()

    async def test_continue_only_truncates_later_messages_without_request(self):
        await self.owner.continue_dialog("ChatGPT", "a1", "Character")
        self.assertEqual(list(self.store.messages), ["u1", "a1"])
        self.assertEqual(self.store.messages["a1"]["text"], "Original answer")
        self.factory.get_provider.assert_not_called()

    async def test_existing_api_provider_still_completes_successful_chat(self):
        self.store.data["character_list"]["Character"]["conversation_method"] = "Open AI"
        await self.chat()
        self.assertEqual(self.store.saved, [(True, "New question"), (False, "Hello world")])
        self.factory.get_provider.assert_called_once_with("Open AI")
        self.assert_buttons_restored()

    def attach_web_bridge(self):
        self.owner.web_bridge = SimpleNamespace(broadcast_message_start=AsyncMock(),
                                               broadcast_chunk=AsyncMock(),
                                               broadcast_message_end=AsyncMock())
        return self.owner.web_bridge

    async def test_success_ends_web_client_stream(self):
        bridge = self.attach_web_bridge()
        await self.chat()
        await asyncio.sleep(0)
        bridge.broadcast_message_end.assert_awaited_once()
        self.assert_buttons_restored()

    async def test_typed_failure_ends_web_client_stream(self):
        bridge = self.attach_web_bridge()
        self.provider.error = ChatGPTProviderError("Usage limit reached")
        await self.chat()
        bridge.broadcast_message_end.assert_awaited_once()
        self.assertEqual(self.store.saved, [])
        self.assert_buttons_restored()

    async def test_cancel_ends_web_client_stream(self):
        bridge = self.attach_web_bridge()
        self.provider.error = asyncio.CancelledError()
        await self.chat()
        bridge.broadcast_message_end.assert_awaited_once()
        self.assertEqual(self.store.saved, [])
        self.assert_buttons_restored()

    async def test_unavailable_web_bridge_does_not_break_error_recovery(self):
        bridge = self.attach_web_bridge()
        bridge.broadcast_message_end.side_effect = RuntimeError("remote body must stay private")
        self.provider.error = ChatGPTAuthError("Sign in again")
        await self.chat()
        self.assertEqual(self.editor.toPlainText(), "New question")
        self.assertEqual(self.store.saved, [])
        self.owner._show_chatgpt_error.assert_called_once_with(self.provider.error)
        self.assert_buttons_restored()
        self.scope["logger"].warning.assert_called_once_with(
            "Could not notify the web client that ChatGPT generation ended.")

    async def test_send_stays_hidden_until_web_stream_cleanup_finishes(self):
        bridge = self.attach_web_bridge()
        entered, release = asyncio.Event(), asyncio.Event()
        async def end():
            entered.set()
            await release.wait()
        bridge.broadcast_message_end.side_effect = end
        self.provider.error = ChatGPTProviderError("Usage limit reached")
        task = asyncio.create_task(self.chat())
        await entered.wait()
        self.assertTrue(self.send.isHidden())
        self.assertEqual(self.editor.toPlainText(), "New question")
        release.set()
        await task
        self.assert_buttons_restored()


class ProviderSettingsRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_switching_chatgpt_back_to_api_restores_key_model_and_sampling_fields(self):
        scope = load_handlers(Mock())
        method = scope["update_api_token"]
        names = {node.attr for node in ast.walk(ast.parse(textwrap.dedent(inspect.getsource(method))))
                 if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Attribute)
                 and node.value.attr == "ui"}
        # Real Qt controls are used for visibility and text; no configuration files.
        ui = SimpleNamespace()
        for name in names:
            control = QtWidgets.QLineEdit() if name.startswith("lineEdit_") else QtWidgets.QWidget()
            setattr(ui, name, control)
        ui.comboBox_reasoning_effort = QtWidgets.QComboBox()
        ui.comboBox_reasoning_effort.addItem("Off", "none")
        ui.comboBox_conversation_method = QtWidgets.QComboBox()
        ui.comboBox_conversation_method.addItems(["Open AI", "ChatGPT", "Anthropic"])
        tokens = {"OPEN_AI_API_TOKEN": "fake-openai", "CUSTOM_ENDPOINT_URL": "https://example.invalid/v1",
                  "ANTHROPIC_API_TOKEN": "fake-anthropic"}
        owner = SimpleNamespace(ui=ui, translations={}, configuration_api=SimpleNamespace(get_token=lambda key: tokens.get(key, "")))
        ui.comboBox_conversation_method.setCurrentText("ChatGPT")
        method(owner)
        self.assertTrue(ui.card_api.isHidden())
        self.assertFalse(ui.chatgpt_settings.isHidden())
        self.assertTrue(ui.chatgpt_unsupported_sampling.isHidden())
        self.assertTrue(ui.chatgpt_unsupported_max_tokens.isHidden())
        ui.comboBox_conversation_method.setCurrentText("Open AI")
        method(owner)
        self.assertFalse(ui.card_api.isHidden())
        self.assertTrue(ui.chatgpt_settings.isHidden())
        self.assertFalse(ui.chatgpt_unsupported_sampling.isHidden())
        self.assertFalse(ui.chatgpt_unsupported_max_tokens.isHidden())
        self.assertFalse(ui.lineEdit_openai_model.isHidden())
        self.assertEqual(ui.lineEdit_api_token_options.text(), "fake-openai")
        self.assertEqual(ui.lineEdit_base_url_options.text(), "https://example.invalid/v1")
        ui.comboBox_conversation_method.setCurrentText("Anthropic")
        method(owner)
        self.assertTrue(ui.lineEdit_openai_model.isHidden())
        self.assertFalse(ui.lineEdit_anthropic_model.isHidden())
        self.assertEqual(ui.lineEdit_api_token_options.text(), "fake-anthropic")
        for control in vars(ui).values():
            control.close()


if __name__ == "__main__":
    unittest.main()
