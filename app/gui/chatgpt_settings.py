"""ChatGPT account controls. Credentials never pass through Qt widgets."""

import asyncio
import threading

from PyQt6 import QtCore, QtWidgets


CHATGPT_DIALOG_STYLE = """
    QMessageBox { background: #202024; }
    QLabel { color: #DEDAD2; background: transparent; font-size: 14px; }
    QPushButton { color: #DEDAD2; background: #303038; border: 1px solid #61616b;
        border-radius: 6px; padding: 8px 14px; min-height: 24px; }
    QPushButton:hover { background: #41414b; }
"""


class ChatGPTSettingsWidget(QtWidgets.QWidget):
    operation_finished = QtCore.pyqtSignal(str, object, object)

    def __init__(self, settings, translations, parent=None, auth=None, model_loader=None):
        super().__init__(parent)
        self.setObjectName("chatgpt_settings")
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            QWidget#chatgpt_settings { background: #141416; border: 1px solid #2d2d31; border-radius: 16px; }
            QLabel { color: #DEDAD2; background: transparent; border: none; font-size: 14px; }
            QComboBox, QPushButton { color: #DEDAD2; background: #202024; border: 1px solid #414147;
                border-radius: 7px; padding: 8px 12px; min-height: 24px; font-size: 14px; }
            QPushButton:hover { background: #303038; border-color: #777780; }
            QPushButton:focus, QComboBox:focus { border-color: #93c5fd; }
            QPushButton:disabled, QComboBox:disabled { color: #92929c; background: #18181c; border-color: #303036; }
            QComboBox QAbstractItemView { color: #DEDAD2; background: #202024;
                selection-background-color: #41414b; selection-color: white; border: 1px solid #414147; }
        """)
        self.settings = settings
        self.translations = translations
        self._auth = auth
        self._model_loader = model_loader
        self._busy = False
        self._operation = None
        self._cancel = threading.Event()
        self._accounts = []
        self._preferred_model = None
        self._account_metadata_busy = False
        self._account_retry = QtCore.QTimer(self)
        self._account_retry.setSingleShot(True)
        self._account_retry.setInterval(1000)
        self._account_retry.timeout.connect(self.refresh_accounts)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)
        self.explanation = QtWidgets.QLabel(self.tr_text("chatgpt_plan_notice"))
        self.explanation.setWordWrap(True)
        layout.addWidget(self.explanation)
        self.accounts = QtWidgets.QComboBox()
        self.accounts.setAccessibleName(self.tr_text("chatgpt_account"))
        self.accounts.setPlaceholderText(self.tr_text("chatgpt_account"))
        layout.addWidget(self.accounts)
        self.status = QtWidgets.QLabel()
        self.status.setWordWrap(True)
        self.status.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        layout.addWidget(self.status)
        row = QtWidgets.QHBoxLayout()
        self.connect_button = QtWidgets.QPushButton(self.tr_text("chatgpt_continue"))
        self.add_button = QtWidgets.QPushButton(self.tr_text("chatgpt_add_account"))
        self.sign_out_button = QtWidgets.QPushButton(self.tr_text("chatgpt_sign_out"))
        self.cancel_button = QtWidgets.QPushButton(self.tr_text("chatgpt_cancel"))
        for button in (self.connect_button, self.add_button, self.sign_out_button, self.cancel_button):
            row.addWidget(button)
        layout.addLayout(row)
        model_row = QtWidgets.QHBoxLayout()
        self.models = QtWidgets.QComboBox()
        self.models.setAccessibleName(self.tr_text("chatgpt_model"))
        self.models.setPlaceholderText(self.tr_text("chatgpt_model"))
        saved_model = settings.get_main_setting("chatgpt_model")
        if saved_model:
            self.models.addItem(saved_model, saved_model)
        self.refresh_button = QtWidgets.QPushButton(self.tr_text("chatgpt_refresh_models"))
        model_row.addWidget(self.models, 1)
        model_row.addWidget(self.refresh_button)
        layout.addLayout(model_row)
        usage = QtWidgets.QLabel('<a style="color: #93c5fd" href="https://chatgpt.com/settings/usage">' + self.tr_text("chatgpt_usage") + '</a>')
        usage.setOpenExternalLinks(True)
        layout.addWidget(usage)
        self.operation_finished.connect(self._finished)
        self.connect_button.clicked.connect(lambda: self.sign_in(self.accounts.currentData()))
        self.add_button.clicked.connect(lambda: self.sign_in(None))
        self.sign_out_button.clicked.connect(self.sign_out)
        self.cancel_button.clicked.connect(self.cancel)
        self.refresh_button.clicked.connect(self.refresh_models)
        self.accounts.activated.connect(self.select_account)
        self.models.activated.connect(self.select_model)
        QtWidgets.QApplication.instance().aboutToQuit.connect(self._cancel.set)
        self.refresh_accounts()

    def tr_text(self, key):
        return self.translations.get(key, ENGLISH[key])

    def auth(self):
        if self._auth is None:
            from app.utils.chatgpt_auth import get_chatgpt_auth
            self._auth = get_chatgpt_auth()
        return self._auth

    def refresh_accounts(self):
        try:
            auth = self.auth()
            read_accounts = getattr(auth, "try_list_accounts", auth.list_accounts)
            accounts = read_accounts()
            if accounts is None:
                # Another worker is refreshing/revoking credentials. Never wait on its lock in Qt.
                self._account_metadata_busy = True
                self.status.setText(self.tr_text("chatgpt_account_busy"))
                self._account_retry.start()
                self._update_buttons()
                return
            self._account_retry.stop()
            self._account_metadata_busy = False
            self._accounts = accounts
        except Exception:
            self._account_metadata_busy = False
            self._accounts = []
            self.status.setText(self.tr_text("chatgpt_storage_error"))
        else:
            active = next((account for account in self._accounts if account.get("active")), None)
            key = "chatgpt_disconnected"
            if active and active.get("connected"):
                key = "chatgpt_connected" if active.get("plan_enabled") else "chatgpt_plan_disabled"
            self.status.setText(self.tr_text(key))
        self.accounts.clear()
        for account in self._accounts:
            self.accounts.addItem(account["label"], account["id"])
            if account.get("active"):
                self.accounts.setCurrentIndex(self.accounts.count() - 1)
        self._update_buttons()

    def _update_buttons(self):
        account = next((a for a in self._accounts if a.get("id") == self.accounts.currentData()), None)
        available = not self._busy and not self._account_metadata_busy
        for widget in (self.accounts, self.connect_button, self.add_button):
            widget.setEnabled(available)
        self.models.setEnabled(available and bool(account and account.get("connected") and account.get("plan_enabled")))
        self.sign_out_button.setEnabled(available and bool(account and account.get("connected")))
        self.refresh_button.setEnabled(available and bool(account and account.get("connected") and account.get("plan_enabled")))
        self.cancel_button.setVisible(self._busy and self._operation != "sign_out")
        self.cancel_button.setEnabled(self._busy)

    def _run(self, name, operation):
        if self._busy:
            return
        self._busy = True
        self._operation = name
        self._cancel.clear()
        self._update_buttons()
        self.status.setText(self.tr_text("chatgpt_waiting" if name == "sign_in" else "chatgpt_working"))

        def worker():
            result, error = None, None
            try:
                result = operation()
            except Exception as exc:
                # Only our auth/provider exceptions are guaranteed to omit secrets.
                if type(exc).__module__ in {"app.utils.chatgpt_auth", "app.utils.ai_clients.providers.chatgpt_provider"}:
                    error = str(exc)
                else:
                    error = self.tr_text("chatgpt_operation_error")
            try:
                self.operation_finished.emit(name, result, error)
            except RuntimeError:
                pass  # Application closed while a bounded network request completed.

        threading.Thread(target=worker, name="ChatGPT-settings", daemon=True).start()

    def sign_in(self, account_id=None):
        self._run("sign_in", lambda: self.auth().sign_in(account_id=account_id, cancel_event=self._cancel))

    def sign_out(self):
        account_id = self.accounts.currentData()
        self._run("sign_out", lambda: self.auth().sign_out(account_id))

    def select_account(self, index):
        # Revalidate the selected registration before making it active.
        self.sign_in(self.accounts.itemData(index))

    def select_model(self, index):
        model = self.models.itemData(index)
        if model:
            self.settings.update_main_setting("chatgpt_model", model)

    def refresh_models(self):
        def load():
            if self._model_loader:
                return self._model_loader()
            from app.utils.ai_clients.providers.chatgpt_provider import ChatGPTProvider
            return asyncio.run(ChatGPTProvider().list_models())
        self._run("models", load)

    def cancel(self):
        self._cancel.set()
        self.cancel_button.setEnabled(False)
        self.status.setText(self.tr_text("chatgpt_cancelling"))

    @QtCore.pyqtSlot(str, object, object)
    def _finished(self, name, result, error):
        cancelled = self._cancel.is_set()
        self._busy = False
        self.refresh_accounts()
        if error:
            self.status.setText(self.tr_text("chatgpt_cancelled") if cancelled else error)
        elif name == "models":
            if cancelled:
                self.status.setText(self.tr_text("chatgpt_cancelled"))
                return
            selected = self.settings.get_main_setting("chatgpt_model") or self._preferred_model
            self._preferred_model = None
            self.models.clear()
            for model in result:
                self.models.addItem(model.get("label", model["id"]), model["id"])
            index = self.models.findData(selected)
            self.models.setCurrentIndex(index if index >= 0 else 0)
            if result:
                self.select_model(self.models.currentIndex())
            else:
                self.settings.update_main_setting("chatgpt_model", "")
                self.status.setText(self.tr_text("chatgpt_no_models"))
        elif name == "sign_out":
            self.models.clear()
            self.settings.update_main_setting("chatgpt_model", "")
            self._preferred_model = None
            if result is False:
                self.status.setText(self.tr_text("chatgpt_revocation_unconfirmed"))
        elif name == "sign_in":
            self._preferred_model = self.settings.get_main_setting("chatgpt_model")
            self.settings.update_main_setting("chatgpt_model", "")
            self.models.clear()
            if result and result.get("plan_enabled"):
                self._welcome()
                self.refresh_models()

    def _welcome(self):
        if self.settings.get_main_setting("chatgpt_welcome_shown"):
            return
        self.settings.update_main_setting("chatgpt_welcome_shown", True)
        self._welcome_dialog = QtWidgets.QMessageBox(self)
        self._welcome_dialog.setStyleSheet(CHATGPT_DIALOG_STYLE)
        self._welcome_dialog.setWindowTitle("ChatGPT")
        self._welcome_dialog.setText(self.tr_text("chatgpt_connected"))
        self._welcome_dialog.setInformativeText(self.tr_text("chatgpt_plan_notice"))
        self._welcome_dialog.addButton(self.tr_text("chatgpt_got_it"), QtWidgets.QMessageBox.ButtonRole.AcceptRole)
        self._welcome_dialog.open()


ENGLISH = {
    "chatgpt_plan_notice": "Eligible requests use your ChatGPT plan. Access depends on your account and app permissions. Chat, memory, summaries, and background character activity all count toward usage. Other cloud features keep their own API settings. Sampling settings and response length are managed by ChatGPT models.",
    "chatgpt_account": "ChatGPT account",
    "chatgpt_continue": "Continue with ChatGPT",
    "chatgpt_add_account": "Add another account",
    "chatgpt_sign_out": "Sign out",
    "chatgpt_cancel": "Cancel",
    "chatgpt_model": "ChatGPT model",
    "chatgpt_refresh_models": "Refresh models",
    "chatgpt_usage": "Manage ChatGPT usage and app access",
    "chatgpt_connected": "Using your ChatGPT plan",
    "chatgpt_got_it": "Got it",
    "chatgpt_disconnected": "Not connected. Continue with ChatGPT to sign in in your browser.",
    "chatgpt_plan_disabled": "Connected, but ChatGPT plan access is disabled. Enable access in ChatGPT settings and reconnect.",
    "chatgpt_storage_error": "Unable to read ChatGPT account storage. Check your operating system credential store.",
    "chatgpt_account_busy": "Account details are being updated. Retrying shortly…",
    "chatgpt_waiting": "Complete sign-in in your browser. You can cancel here.",
    "chatgpt_working": "Connecting to ChatGPT…",
    "chatgpt_operation_error": "ChatGPT operation failed. Check your connection and try again.",
    "chatgpt_cancelling": "Cancelling…",
    "chatgpt_cancelled": "Operation cancelled.",
    "chatgpt_no_models": "No eligible models are available for this account.",
    "chatgpt_revocation_unconfirmed": "Signed out locally. Remote revocation could not be confirmed; disconnect this app in ChatGPT Settings.",
}
