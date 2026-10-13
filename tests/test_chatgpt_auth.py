"""Offline security and lifecycle tests; use generated keys and fake tokens only."""

import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from http.server import HTTPServer
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlsplit

import jwt
import requests
from cryptography.hazmat.primitives.asymmetric import rsa

from app.utils.chatgpt_auth import (
    AUTHORIZE_URL, DIRECT_SCOPE, DYNAMIC_CLIENT, ISSUER, RESOURCE, TOKEN_URL,
    ChatGPTAuthError, ChatGPTAuthManager, CredentialStore,
)


class Response:
    def __init__(self, value=None, status=200):
        self.value, self.status_code = value, status

    def json(self):
        return self.value


class FakeSession:
    def __init__(self):
        self.calls = []
        self.responses = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def tokens(**updates):
    result = dict(access_token="fake-access", refresh_token="fake-refresh", id_token="fake-id",
                  token_type="Bearer", expires_in=3600, scope="openid " + DIRECT_SCOPE)
    result.update(updates)
    return result


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = CredentialStore(Path(self.temp.name) / "auth")
        self.session = FakeSession()
        self.manager = ChatGPTAuthManager(self.store, self.session)
        self.manager._discovery_cache = {"issuer": ISSUER, "jwks_uri": ISSUER + "/keys",
                                         "revocation_endpoint": ISSUER + "/revoke"}

    def seed(self, client="oaiapp_first", subject="user1", expires_at=None):
        with self.store.locked():
            data = self.store.read()
            data["accounts"][client] = dict(client_id=client, subject=subject, issuer=ISSUER,
                email="same@example.test", access_token="old-access", refresh_token="old-refresh",
                id_token="old-id", scopes=[DIRECT_SCOPE], expires_at=expires_at or time.time() + 3600)
            data["active"] = client
            self.store.write(data)

    def read(self):
        with self.store.locked():
            return self.store.read()

    def browser(self, mutate=None):
        """Return callback opener; asynchronous request lets listener run."""
        def open_browser(url):
            self.assertTrue(url.startswith(AUTHORIZE_URL + "?"))
            params = {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}
            self.auth_params = params
            callback = dict(state=params["state"], code="fake-code", client_id="oaiapp_first")
            if mutate:
                mutate(callback)
            self.callback_status = None

            def send():
                self.callback_status = requests.get(params["redirect_uri"] + "?" + urlencode(callback), timeout=5).status_code

            self.callback_thread = threading.Thread(target=send)
            self.callback_thread.start()
            return True
        return open_browser

    def login(self, **kwargs):
        self.session.responses = [Response(tokens())]
        with patch.object(self.manager, "_verify_identity", return_value={"sub": "user1", "email": "same@example.test"}) as verify:
            account = self.manager.sign_in(open_browser=self.browser(), **kwargs)
            self.callback_thread.join(5)
            self.assertEqual(verify.call_args.args[2], self.auth_params["nonce"])
        return account

    def test_dynamic_login_pkce_loopback_and_issued_client(self):
        account = self.login()
        self.assertTrue(account["plan_enabled"])
        self.assertEqual(self.auth_params["client_id"], DYNAMIC_CLIENT)
        self.assertEqual(self.auth_params["agent_name_hint"], "Soul of Waifu")
        self.assertEqual(self.auth_params["code_challenge_method"], "S256")
        self.assertTrue(self.auth_params["redirect_uri"].startswith("http://127.0.0.1:"))
        exchange = self.session.calls[0][2]["data"]
        self.assertEqual(exchange["client_id"], "oaiapp_first")
        self.assertEqual(exchange["redirect_uri"], self.auth_params["redirect_uri"])
        self.assertEqual(exchange["resource"], RESOURCE)
        import base64
        import hashlib
        challenge = base64.urlsafe_b64encode(hashlib.sha256(exchange["code_verifier"].encode()).digest()).decode().rstrip("=")
        self.assertEqual(challenge, self.auth_params["code_challenge"])
        self.assertFalse(self.session.calls[0][2]["allow_redirects"])

    def test_returning_login_reuses_host_client_and_hints(self):
        self.seed()
        original = self.read()
        self.login(account_id="oaiapp_first")
        self.assertEqual(self.auth_params["client_id"], "oaiapp_first")
        self.assertEqual(self.auth_params["ext_agent_host_id"], original["host_id"])
        self.assertEqual(self.auth_params["id_token_hint"], "old-id")
        self.assertNotIn("agent_name_hint", self.auth_params)

    def test_bad_state_never_exchanges_code(self):
        with self.assertRaisesRegex(ChatGPTAuthError, "timed out"):
            self.manager.sign_in(open_browser=self.browser(lambda q: q.update(state="wrong")), timeout=0.4)
        self.callback_thread.join(5)
        self.assertEqual(self.callback_status, 400)
        self.assertEqual(self.session.calls, [])

    def test_declined_callback_does_not_exchange(self):
        with self.assertRaisesRegex(ChatGPTAuthError, "declined"):
            self.manager.sign_in(open_browser=self.browser(lambda q: q.update(error="access_denied")))
        self.callback_thread.join(5)
        self.assertEqual(self.session.calls, [])

    def test_reauth_rejects_changed_client_without_exchange(self):
        self.seed()
        with self.assertRaisesRegex(ChatGPTAuthError, "different account registration"):
            self.manager.sign_in("oaiapp_first", open_browser=self.browser(lambda q: q.update(client_id="oaiapp_other")))
        self.callback_thread.join(5)
        self.assertEqual(self.session.calls, [])
        self.assertEqual(self.manager.get_access_token(), "old-access")

    def test_reauth_rejects_changed_subject_preserving_tokens(self):
        self.seed()
        self.session.responses = [Response(tokens()), Response(None)]
        with patch.object(self.manager, "_verify_identity", return_value={"sub": "other"}):
            with self.assertRaisesRegex(ChatGPTAuthError, "different account"):
                self.manager.sign_in("oaiapp_first", open_browser=self.browser())
        self.callback_thread.join(5)
        self.assertEqual(self.manager.get_access_token(), "old-access")

    def test_missing_client_id_does_not_exchange(self):
        with self.assertRaisesRegex(ChatGPTAuthError, "client ID"):
            self.manager.sign_in(open_browser=self.browser(lambda q: q.pop("client_id")))
        self.callback_thread.join(5)
        self.assertEqual(self.session.calls, [])

    def test_expired_code_starts_fresh_authorization_with_issued_client(self):
        self.session.responses = [Response({"error": "invalid_grant"}, 400), Response(tokens())]
        attempts = []
        opener = self.browser()

        def browser(url):
            attempts.append(parse_qs(urlsplit(url).query))
            return opener(url)

        with patch.object(self.manager, "_verify_identity", return_value={"sub": "user1"}):
            self.manager.sign_in(open_browser=browser)
        self.callback_thread.join(5)
        self.assertEqual(attempts[0]["client_id"], [DYNAMIC_CLIENT])
        self.assertEqual(attempts[1]["client_id"], ["oaiapp_first"])
        self.assertNotEqual(attempts[0]["state"], attempts[1]["state"])
        self.assertNotEqual(attempts[0]["nonce"], attempts[1]["nonce"])
        self.assertNotIn("agent_name_hint", attempts[1])

    def test_cancel_closes_listener_and_preserves_active(self):
        self.seed()
        cancel = threading.Event()
        cancel.set()
        with self.assertRaisesRegex(ChatGPTAuthError, "cancelled"):
            self.manager.sign_in(cancel_event=cancel, open_browser=lambda _: True)
        self.assertEqual(self.manager.get_access_token(), "old-access")

    def test_refresh_rotates_and_persists_with_issued_client(self):
        self.seed(expires_at=1)
        self.session.responses = [Response(tokens(id_token=None, refresh_token="rotated"))]
        self.assertEqual(self.manager.get_access_token(), "fake-access")
        self.assertEqual(self.read()["accounts"]["oaiapp_first"]["refresh_token"], "rotated")
        request = self.session.calls[0][2]["data"]
        self.assertEqual(request["client_id"], "oaiapp_first")
        self.assertEqual(request["refresh_token"], "old-refresh")
        self.assertNotIn("scope", request)
        self.assertEqual(self.manager.get_access_token(), "fake-access")
        self.assertEqual(len(self.session.calls), 1)

    def test_offline_grant_requires_refresh_token(self):
        with self.assertRaises(ChatGPTAuthError):
            self.manager._apply_tokens({}, tokens(refresh_token=None, scope="openid offline_access " + DIRECT_SCOPE))

    def test_two_managers_serialize_refresh(self):
        self.seed(expires_at=1)
        self.session.responses = [Response(tokens(id_token=None))]
        second = ChatGPTAuthManager(CredentialStore(self.store.directory), self.session)
        results = []
        workers = [threading.Thread(target=lambda m=m: results.append(m.get_access_token())) for m in (self.manager, second)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(5)
        self.assertEqual(results, ["fake-access", "fake-access"])
        self.assertEqual(len(self.session.calls), 1)

    def test_revoked_refresh_clears_tokens_retains_mapping(self):
        self.seed(expires_at=1)
        self.session.responses = [Response({"error": "invalid_grant"}, 400)]
        with self.assertRaisesRegex(ChatGPTAuthError, "expired or was revoked"):
            self.manager.get_access_token()
        account = self.read()["accounts"]["oaiapp_first"]
        self.assertEqual(account["subject"], "user1")
        self.assertNotIn("access_token", account)

    def test_refresh_network_error_preserves_tokens_and_redacts_details(self):
        self.seed(expires_at=1)
        self.session.responses = [requests.ConnectionError("SECRET old-refresh")]
        with self.assertRaises(ChatGPTAuthError) as error:
            self.manager.get_access_token()
        self.assertNotIn("SECRET", str(error.exception))
        self.assertEqual(self.read()["accounts"]["oaiapp_first"]["refresh_token"], "old-refresh")

    def test_identity_only_scope_disables_inference(self):
        self.session.responses = [Response(tokens(scope="openid email"))]
        with patch.object(self.manager, "_verify_identity", return_value={"sub": "user1"}):
            result = self.manager.sign_in(open_browser=self.browser())
        self.callback_thread.join(5)
        self.assertFalse(result["plan_enabled"])
        with self.assertRaisesRegex(ChatGPTAuthError, "not enabled"):
            self.manager.get_access_token()

    def test_identity_only_without_access_token_is_retained(self):
        self.session.responses = [Response({"id_token": "fake-id", "scope": "openid email"})]
        with patch.object(self.manager, "_verify_identity", return_value={"sub": "user1"}):
            result = self.manager.sign_in(open_browser=self.browser())
        self.callback_thread.join(5)
        self.assertTrue(result["connected"])
        self.assertFalse(result["plan_enabled"])
        with self.assertRaisesRegex(ChatGPTAuthError, "not enabled"):
            self.manager.get_access_token()

    def test_logout_revoke_empty_success_keeps_host_and_mapping(self):
        self.seed()
        before = self.read()
        self.manager._discovery_cache = {"revocation_endpoint": ISSUER + "/revoke"}
        self.session.responses = [Response(None)]
        self.assertTrue(self.manager.sign_out())
        after = self.read()
        self.assertEqual(before["host_id"], after["host_id"])
        self.assertEqual(after["accounts"]["oaiapp_first"]["subject"], "user1")
        self.assertFalse(self.manager.active_account()["connected"])
        self.assertNotIn("id_token", after["accounts"]["oaiapp_first"])

    def test_logout_network_failure_still_clears_locally(self):
        self.seed()
        self.manager._discovery_cache = {"revocation_endpoint": ISSUER + "/revoke"}
        self.session.responses = [requests.ConnectionError(), requests.ConnectionError()]
        self.assertFalse(self.manager.sign_out())
        self.assertFalse(self.manager.active_account()["connected"])

    def test_logout_without_refresh_does_not_claim_remote_revocation(self):
        self.seed()
        with self.store.locked():
            data = self.store.read()
            data["accounts"]["oaiapp_first"].pop("refresh_token")
            self.store.write(data)
        self.assertFalse(self.manager.sign_out())
        self.assertFalse(self.manager.active_account()["connected"])

    def test_account_picker_labels_distinguish_same_email(self):
        self.seed()
        self.seed("oaiapp_second")
        accounts = self.manager.list_accounts()
        self.assertNotEqual(accounts[0]["label"], accounts[1]["label"])
        self.assertNotIn("access_token", accounts[0])
        self.manager.set_active_account("oaiapp_first")
        self.assertEqual(self.manager.active_account()["id"], "oaiapp_first")

    def test_storage_protection_and_atomic_write(self):
        self.seed()
        raw = self.store.path.read_bytes()
        if os.name == "nt":
            self.assertNotIn(b"old-refresh", raw)
            self.assertNotIn(b"old-access", raw)
        else:
            self.assertEqual(self.store.path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(self.store.directory.stat().st_mode & 0o777, 0o700)
        self.assertEqual(list(self.store.directory.glob(".credentials-*")), [])

    def test_untrusted_discovery_endpoints_rejected(self):
        for url in ("http://auth.openai.com/keys", "https://evil.test/keys", "https://user@auth.openai.com/keys", "https://auth.openai.com:bad/keys"):
            with self.subTest(url=url), self.assertRaises(ChatGPTAuthError):
                self.manager._trusted_url(url)

    def test_cancel_after_callback_prevents_exchange_and_closes_listener(self):
        cancel = threading.Event()

        class CancellingServer(HTTPServer):
            def handle_request(inner):
                super().handle_request()
                cancel.set()

        with patch("app.utils.chatgpt_auth.HTTPServer", CancellingServer):
            with self.assertRaisesRegex(ChatGPTAuthError, "cancelled"):
                self.manager.sign_in(cancel_event=cancel, open_browser=self.browser())
        self.callback_thread.join(5)
        self.assertEqual(self.session.calls, [])
        with self.assertRaises(requests.ConnectionError):
            requests.get(self.auth_params["redirect_uri"], timeout=1)

    def test_cancel_during_token_exchange_revokes_unpersisted_tokens(self):
        cancel = threading.Event()
        request = self.session.request

        def cancel_on_exchange(method, url, **kwargs):
            response = request(method, url, **kwargs)
            if url == TOKEN_URL:
                cancel.set()
            return response

        self.session.responses = [Response(tokens()), Response(None)]
        with patch.object(self.session, "request", side_effect=cancel_on_exchange):
            with patch.object(self.manager, "_verify_identity") as verify:
                with self.assertRaisesRegex(ChatGPTAuthError, "cancelled"):
                    self.manager.sign_in(cancel_event=cancel, open_browser=self.browser())
                verify.assert_not_called()
        self.callback_thread.join(5)
        self.assertEqual(self.session.calls[-1][1], ISSUER + "/revoke")
        self.assertEqual(self.read()["accounts"], {})

    def test_cancel_before_commit_preserves_existing_session(self):
        self.seed()
        cancel = threading.Event()
        self.session.responses = [Response(tokens()), Response(None)]

        def identity(*_args):
            cancel.set()
            return {"sub": "user1"}

        with patch.object(self.manager, "_verify_identity", side_effect=identity):
            with self.assertRaisesRegex(ChatGPTAuthError, "cancelled"):
                self.manager.sign_in("oaiapp_first", cancel_event=cancel, open_browser=self.browser())
        self.callback_thread.join(5)
        self.assertEqual(self.manager.get_access_token(), "old-access")

    def test_cancel_cleanup_failure_is_reported_without_activating_session(self):
        cancel = threading.Event()
        self.session.responses = [Response(tokens()), Response(None, 503), Response(None, 503)]

        def identity(*_args):
            cancel.set()
            return {"sub": "user1"}

        with patch.object(self.manager, "_verify_identity", side_effect=identity):
            with self.assertRaisesRegex(ChatGPTAuthError, "Remote revocation was not confirmed"):
                self.manager.sign_in(cancel_event=cancel, open_browser=self.browser())
        self.callback_thread.join(5)
        self.assertEqual(self.read()["accounts"], {})

    def test_late_signin_does_not_undo_account_switch(self):
        self.seed("oaiapp_second")
        self.seed()
        self.session.responses = [Response(tokens()), Response(None)]
        other = ChatGPTAuthManager(CredentialStore(self.store.directory))

        def identity(*_args):
            other.set_active_account("oaiapp_second")
            return {"sub": "user1"}

        with patch.object(self.manager, "_verify_identity", side_effect=identity):
            with self.assertRaisesRegex(ChatGPTAuthError, "newer choice was preserved"):
                self.manager.sign_in("oaiapp_first", open_browser=self.browser())
        self.callback_thread.join(5)
        self.assertEqual(self.manager.active_account()["id"], "oaiapp_second")
        self.assertEqual(self.read()["accounts"]["oaiapp_first"]["access_token"], "old-access")

    def test_late_signin_does_not_undo_signout(self):
        self.seed()
        self.session.responses = [Response(tokens()), Response(None)]
        other_session = FakeSession()
        other_session.responses = [Response(None)]
        other = ChatGPTAuthManager(CredentialStore(self.store.directory), other_session)
        other._discovery_cache = self.manager._discovery_cache

        def identity(*_args):
            self.assertTrue(other.sign_out())
            return {"sub": "user1"}

        with patch.object(self.manager, "_verify_identity", side_effect=identity):
            with self.assertRaisesRegex(ChatGPTAuthError, "newer choice was preserved"):
                self.manager.sign_in("oaiapp_first", open_browser=self.browser())
        self.callback_thread.join(5)
        self.assertFalse(self.manager.active_account()["connected"])

    def test_two_signins_in_same_manager_are_rejected(self):
        self.manager._sign_in_lock.acquire()
        try:
            with self.assertRaisesRegex(ChatGPTAuthError, "already in progress"):
                self.manager.sign_in(open_browser=lambda _: self.fail("Browser opened"))
        finally:
            self.manager._sign_in_lock.release()

    def test_pinned_request_rejects_changed_active_account(self):
        self.seed()
        self.seed("oaiapp_second")
        with self.assertRaisesRegex(ChatGPTAuthError, "account changed"):
            self.manager.get_access_token(force_refresh=True, expected_account_id="oaiapp_first")
        self.assertEqual(self.session.calls, [])

    def test_ui_snapshot_does_not_wait_for_refresh_lock(self):
        self.seed()
        other = CredentialStore(self.store.directory)
        with other.locked():
            started = time.monotonic()
            self.assertIsNone(self.manager.try_list_accounts())
            self.assertLess(time.monotonic() - started, 0.2)
        self.assertEqual(self.manager.try_list_accounts()[0]["id"], "oaiapp_first")

    def test_terminal_refresh_codes_clear_credentials(self):
        for code in ("invalid_refresh_token", "token_expired", "refresh_token_expired",
                     "refresh_token_reused", "refresh_token_invalidated"):
            self.seed(expires_at=1)
            self.session.responses = [Response({"error": code}, 400)]
            with self.subTest(code=code), self.assertRaises(ChatGPTAuthError):
                self.manager.get_access_token()
            self.assertFalse(self.manager.active_account()["connected"])

    def test_explicit_enable_plan_requests_consent(self):
        self.seed()
        with self.store.locked():
            data = self.store.read()
            data["accounts"]["oaiapp_first"]["scopes"] = ["openid"]
            self.store.write(data)
        self.login(account_id="oaiapp_first")
        self.assertEqual(self.auth_params["prompt"], "consent")

    def test_signout_waits_for_refresh_then_revokes_rotated_token(self):
        self.seed(expires_at=1)
        entered = threading.Event()
        release = threading.Event()
        request = self.session.request
        self.session.responses = [Response(tokens(id_token=None, refresh_token="rotated"))]

        def slow_refresh(*args, **kwargs):
            entered.set()
            if not release.wait(5):
                raise AssertionError("Refresh barrier timed out")
            return request(*args, **kwargs)

        other_session = FakeSession()
        other_session.responses = [Response(None)]
        other = ChatGPTAuthManager(CredentialStore(self.store.directory), other_session)
        other._discovery_cache = self.manager._discovery_cache
        results, errors = [], []

        def run(action):
            try:
                results.append(action())
            except Exception as error:
                errors.append(error)

        with patch.object(self.session, "request", side_effect=slow_refresh):
            refresh_worker = threading.Thread(target=run, args=(self.manager.get_access_token,))
            refresh_worker.start()
            self.assertTrue(entered.wait(5))
            logout_worker = threading.Thread(target=run, args=(other.sign_out,))
            logout_worker.start()
            self.assertFalse(other_session.calls)
            release.set()
            refresh_worker.join(5)
            logout_worker.join(5)
        self.assertFalse(errors)
        self.assertEqual(len(results), 2)
        self.assertEqual(other_session.calls[-1][2]["data"]["token"], "rotated")
        self.assertFalse(self.manager.active_account()["connected"])

    def test_refresh_scope_loss_persists_rotation_and_blocks_inference(self):
        self.seed(expires_at=1)
        self.session.responses = [Response(tokens(id_token=None, scope="openid", refresh_token="rotated"))]
        with self.assertRaisesRegex(ChatGPTAuthError, "permission was removed"):
            self.manager.get_access_token()
        self.assertEqual(self.read()["accounts"]["oaiapp_first"]["refresh_token"], "rotated")
        with self.assertRaisesRegex(ChatGPTAuthError, "not enabled"):
            self.manager.get_access_token()
        self.assertEqual(len(self.session.calls), 1)

    def test_refresh_omitted_scope_preserves_existing_grant(self):
        self.seed(expires_at=1)
        self.session.responses = [Response(tokens(id_token=None, scope=None))]
        self.assertEqual(self.manager.get_access_token(), "fake-access")
        self.assertTrue(self.manager.active_account()["plan_enabled"])

    def test_refresh_malformed_payload_does_not_replace_old_tokens(self):
        self.seed(expires_at=1)
        for changed in (dict(token_type=None), dict(expires_in="not-a-number"), dict(refresh_token=None),
                        dict(scope=[]), dict(access_token={"secret": "not-a-string"})):
            self.session.responses = [Response(tokens(id_token=None, **changed))]
            with self.subTest(changed=changed), self.assertRaises(ChatGPTAuthError):
                self.manager.get_access_token()
            self.assertEqual(self.read()["accounts"]["oaiapp_first"]["access_token"], "old-access")

    def test_http_error_and_redirect_never_expose_response_content(self):
        for response in (Response({"error": {"message": "SECRET"}}, 500), Response("SECRET", 302),
                         Response("SECRET", 200), Response({"error": "SECRET"}, 429)):
            self.session.responses = [response]
            with self.subTest(status=response.status_code), self.assertRaises(ChatGPTAuthError) as error:
                self.manager._json_request("POST", TOKEN_URL, data={})
            self.assertNotIn("SECRET", str(error.exception))

    def test_atomic_replace_failure_keeps_original_and_removes_temporary(self):
        self.seed()
        original = self.store.path.read_bytes()
        with patch("app.utils.chatgpt_auth.os.replace", side_effect=OSError("SECRET")):
            with self.assertRaises(ChatGPTAuthError) as error:
                with self.store.locked():
                    data = self.store.read()
                    data["accounts"]["oaiapp_first"]["access_token"] = "new-access"
                    self.store.write(data)
        self.assertNotIn("SECRET", str(error.exception))
        self.assertEqual(self.store.path.read_bytes(), original)
        self.assertEqual(list(self.store.directory.glob(".credentials-*")), [])

    def test_corrupt_storage_shape_is_sanitized_without_overwriting(self):
        from app.utils.chatgpt_auth import _dpapi
        for malformed in ([], {"version": 1, "host_id": "host", "accounts": {"a": "SECRET"}},
                          {"version": 1, "host_id": "host", "accounts": {}, "active": "absent"}):
            with self.store.locked():
                raw = json.dumps(malformed).encode()
                self.store.path.write_bytes(_dpapi(raw) if os.name == "nt" else raw)
                before = self.store.path.read_bytes()
            with self.subTest(malformed=malformed), self.assertRaises(ChatGPTAuthError) as error:
                self.manager.list_accounts()
            self.assertNotIn("SECRET", str(error.exception))
            self.assertEqual(before, self.store.path.read_bytes())


class IdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(cls.private.public_key()))
        cls.jwk.update(kid="test-key", alg="RS256", use="sig")

    def setUp(self):
        self.session = FakeSession()
        self.manager = ChatGPTAuthManager(session=self.session)
        self.manager._jwks_cache = (time.time(), [self.jwk])
        self.claims = dict(iss=ISSUER, aud="oaiapp_test", sub="user", iat=int(time.time()),
                           exp=int(time.time()) + 3600, nonce="expected")

    def sign(self, claims=None, key=None, kid="test-key"):
        return jwt.encode(claims or self.claims, key or self.private, algorithm="RS256", headers={"kid": kid})

    def test_valid_identity(self):
        self.assertEqual(self.manager._verify_identity(self.sign(), "oaiapp_test", "expected")["sub"], "user")

    def test_identity_claim_mismatches_and_expiry(self):
        for field, value in (("iss", "https://evil.test"), ("aud", "other"), ("nonce", "wrong"),
                             ("exp", int(time.time()) - 60), ("sub", ""), ("azp", "other")):
            claims = dict(self.claims, **{field: value})
            with self.subTest(field=field), self.assertRaises(ChatGPTAuthError):
                self.manager._verify_identity(self.sign(claims), "oaiapp_test", "expected")

    def test_rejects_forged_signature(self):
        attacker = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        with self.assertRaises(ChatGPTAuthError):
            self.manager._verify_identity(self.sign(key=attacker), "oaiapp_test", "expected")

    def test_unknown_kid_refreshes_trusted_jwks(self):
        self.manager._discovery_cache = {"jwks_uri": ISSUER + "/keys"}
        rotated = dict(self.jwk, kid="rotated")
        self.session.responses = [Response({"keys": [rotated]})]
        self.manager._verify_identity(self.sign(kid="rotated"), "oaiapp_test", "expected")
        self.assertEqual(self.session.calls[0][1], ISSUER + "/keys")

    def test_unsigned_identity_rejected(self):
        token = jwt.encode(self.claims, key="", algorithm="none")
        with self.assertRaises(ChatGPTAuthError):
            self.manager._verify_identity(token, "oaiapp_test", "expected")

    def test_missing_required_claims_and_malformed_tokens(self):
        for field in ("iss", "aud", "sub", "exp", "iat", "nonce"):
            claims = dict(self.claims)
            claims.pop(field)
            with self.subTest(field=field), self.assertRaises(ChatGPTAuthError):
                self.manager._verify_identity(self.sign(claims), "oaiapp_test", "expected")
        for token in (None, "", "invalid.jwt.value", {"unexpected": "object"}):
            with self.subTest(token=token), self.assertRaises(ChatGPTAuthError):
                self.manager._verify_identity(token, "oaiapp_test", "expected")

    def test_multi_audience_requires_matching_authorized_party(self):
        claims = dict(self.claims, aud=["oaiapp_test", "other"])
        with self.assertRaises(ChatGPTAuthError):
            self.manager._verify_identity(self.sign(claims), "oaiapp_test", "expected")
        claims["azp"] = "oaiapp_test"
        self.assertEqual(self.manager._verify_identity(self.sign(claims), "oaiapp_test", "expected")["sub"], "user")

    def test_unexpected_jwks_shape_is_sanitized(self):
        self.manager._discovery_cache = {"jwks_uri": ISSUER + "/keys"}
        for keys in (None, [None], ["SECRET"]):
            self.manager._jwks_cache = None
            self.session.responses = [Response({"keys": keys}), Response({"keys": keys})]
            with self.subTest(keys=keys), self.assertRaises(ChatGPTAuthError) as error:
                self.manager._verify_identity(self.sign(), "oaiapp_test", "expected")
            self.assertNotIn("SECRET", str(error.exception))


if __name__ == "__main__":
    unittest.main()
