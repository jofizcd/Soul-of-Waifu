"""Qt account-flow regressions with fake auth, no browser or real credentials."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import threading
import time
import unittest
import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from PyQt6 import QtCore, QtWidgets
from app.gui.chatgpt_settings import ChatGPTSettingsWidget, ENGLISH
import yaml


class Settings:
    def __init__(self):
        self.data = {"chatgpt_model": "existing", "chatgpt_welcome_shown": True}

    def get_main_setting(self, key):
        return self.data.get(key)

    def update_main_setting(self, key, value):
        self.data[key] = value


class Auth:
    def __init__(self):
        self.accounts = [{"id": "a", "label": "Personal", "active": True,
                          "connected": True, "plan_enabled": True},
                         {"id": "b", "label": "Work", "active": False,
                          "connected": False, "plan_enabled": False}]
        self.selected = None
        self.entered = threading.Event()
        self.hold_signin = False

    def list_accounts(self):
        return self.accounts

    def sign_in(self, account_id=None, cancel_event=None):
        self.selected = account_id
        self.entered.set()
        if self.hold_signin:
            cancel_event.wait(2)
            raise RuntimeError("sensitive remote response must not appear")
        account_id = account_id or "a"
        for account in self.accounts:
            account["active"] = account["id"] == account_id
            if account["active"]:
                account.update(connected=True, plan_enabled=True)
        return next(a for a in self.accounts if a["active"])

    def sign_out(self, account_id):
        next(a for a in self.accounts if a["id"] == account_id)["connected"] = False
        return False


class ChatGPTSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.settings, self.auth = Settings(), Auth()
        self.widget = ChatGPTSettingsWidget(self.settings, {}, auth=self.auth,
            model_loader=lambda: [{"id": "other", "label": "Other"},
                                  {"id": "existing", "label": "Existing"}])

    def tearDown(self):
        self.widget._cancel.set()
        self.wait_until(lambda: not self.widget._busy)
        self.widget.close()

    def wait_until(self, predicate):
        deadline = time.monotonic() + 3
        while not predicate() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.005)
        self.app.processEvents()
        self.assertTrue(predicate())

    def test_account_switch_reauthorizes_before_model_discovery(self):
        self.widget.select_account(1)
        self.wait_until(lambda: not self.widget._busy)
        self.assertEqual(self.auth.selected, "b")
        self.assertEqual(self.widget.accounts.currentData(), "b")
        self.assertEqual(self.widget.models.currentData(), "existing")
        self.widget.select_model(0)
        self.assertEqual(self.settings.data["chatgpt_model"], "other")

    def test_cancelled_signin_keeps_qt_responsive_and_sanitizes_error(self):
        self.auth.hold_signin = True
        ticks = []
        QtCore.QTimer.singleShot(0, lambda: ticks.append(True))
        self.widget.sign_in("a")
        self.wait_until(self.auth.entered.is_set)
        self.assertTrue(ticks)
        self.widget.cancel()
        self.wait_until(lambda: not self.widget._busy)
        self.assertEqual(self.widget.status.text(), "Operation cancelled.")
        self.assertTrue(self.auth.accounts[0]["connected"])

    def test_signout_reports_unconfirmed_revocation(self):
        self.widget.sign_out()
        self.wait_until(lambda: not self.widget._busy)
        self.assertIn("Remote revocation could not be confirmed", self.widget.status.text())
        self.assertFalse(self.widget.refresh_button.isEnabled())

    def test_empty_model_catalog_clears_stale_selection(self):
        self.widget._model_loader = lambda: []
        self.widget.refresh_models()
        self.wait_until(lambda: not self.widget._busy)
        self.assertEqual(self.settings.data["chatgpt_model"], "")
        self.assertEqual(self.widget.models.count(), 0)

    def test_model_discovery_failure_does_not_echo_remote_data(self):
        def fail():
            raise RuntimeError("Authorization: secret")
        self.widget._model_loader = fail
        self.widget.refresh_models()
        self.wait_until(lambda: not self.widget._busy)
        self.assertNotIn("secret", self.widget.status.text())
        self.assertIn("failed", self.widget.status.text())

    def test_new_account_catalog_failure_clears_previous_model(self):
        def fail():
            raise RuntimeError("offline")
        self.widget._model_loader = fail
        self.widget.sign_in("b")
        self.wait_until(lambda: not self.widget._busy)
        self.assertEqual(self.settings.data["chatgpt_model"], "")
        self.assertEqual(self.widget.models.count(), 0)

    def test_late_cancel_after_auth_commit_does_not_keep_old_model(self):
        def fail():
            raise RuntimeError("offline")
        self.widget._model_loader = fail
        account = self.auth.sign_in("b")
        self.widget._cancel.set()
        self.widget._finished("sign_in", account, None)
        self.wait_until(lambda: not self.widget._busy)
        self.assertEqual(self.widget.accounts.currentData(), "b")
        self.assertEqual(self.settings.data["chatgpt_model"], "")
        self.assertEqual(self.widget.models.count(), 0)

    def test_busy_account_store_preserves_responsiveness_and_retries(self):
        self.auth.try_list_accounts = lambda: None
        ticks = []
        QtCore.QTimer.singleShot(0, lambda: ticks.append(True))
        start = time.monotonic()
        self.widget.refresh_accounts()
        self.assertLess(time.monotonic() - start, .2)
        self.app.processEvents()
        self.assertTrue(ticks)
        self.assertTrue(self.widget._account_retry.isActive())
        self.assertFalse(self.widget.sign_out_button.isEnabled())
        self.auth.try_list_accounts = self.auth.list_accounts
        self.widget.refresh_accounts()
        self.assertFalse(self.widget._account_retry.isActive())
        self.assertTrue(self.widget.sign_out_button.isEnabled())

    def test_first_success_notice_is_shown_once(self):
        self.settings.data["chatgpt_welcome_shown"] = False
        self.widget._welcome()
        dialog = self.widget._welcome_dialog
        self.assertTrue(self.settings.data["chatgpt_welcome_shown"])
        self.assertTrue(dialog.isVisible())
        dialog.close()
        self.widget._welcome()
        self.assertIs(self.widget._welcome_dialog, dialog)
        self.assertFalse(dialog.isVisible())

    def test_english_and_russian_cover_all_account_controls(self):
        root = Path(__file__).parents[1]
        for language in ("en", "ru"):
            translations = yaml.safe_load((root / f"app/translations/{language}.yaml").read_text(encoding="utf-8"))
            self.assertFalse(set(ENGLISH) - set(translations))
            self.assertIn("ChatGPT", translations["chatgpt_continue"])
            self.assertIn("ChatGPT", translations["chatgpt_plan_notice"])


class ToolLoopFailureTests(unittest.TestCase):
    def test_auth_and_plan_errors_do_not_retry_as_plain_generation(self):
        # Load this method alone: importing the application also loads speech/GPU engines.
        source = Path(__file__).parents[1] / "app/gui/interface_signals.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        method = next(node for node in ast.walk(tree)
                      if isinstance(node, ast.AsyncFunctionDef) and node.name == "run_tool_loop")
        class AuthError(Exception):
            pass
        class ProviderError(Exception):
            pass
        scope = {"ChatGPTAuthError": AuthError, "ChatGPTProviderError": ProviderError}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), "exec"), scope)
        registry = SimpleNamespace(has_tools=lambda: True, get_schemas=lambda: [])
        owner = SimpleNamespace(tool_registry=registry, MAX_TOOL_LOOP_ITERATIONS=4)
        for error in (AuthError, ProviderError):
            provider = SimpleNamespace(generate=AsyncMock(side_effect=error("not authorized")))
            with self.assertRaises(error):
                scope["run_tool_loop"](owner, provider, [], "Character", "User").send(None)
            self.assertEqual(provider.generate.await_count, 1)


if __name__ == "__main__":
    unittest.main()
