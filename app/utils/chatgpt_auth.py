"""Public-client Sign in with ChatGPT, isolated from application exports.

Credentials belong to this application: never import Codex/browser credentials.
Windows storage uses current-user DPAPI; POSIX storage is owner-only (0600).
The cross-process lock covers token rotation and atomic credential replacement.
"""

import base64
import ctypes
import hashlib
import json
import math
import os
import secrets
import tempfile
import threading
import time
import uuid
import webbrowser
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

import jwt
import requests
from filelock import FileLock, Timeout


ISSUER = "https://auth.openai.com"
AUTHORIZE_URL = ISSUER + "/api/accounts/authorize"
TOKEN_URL = ISSUER + "/api/accounts/oauth/token"
RESOURCE = "https://api.openai.com/v1"
DIRECT_SCOPE = "chatgpt.tokens.use.direct"
SCOPES = "openid profile email offline_access resource.invoke " + DIRECT_SCOPE
DYNAMIC_CLIENT = "dynamic_agent_client"
CALLBACK_PATH = "/auth/callback"


class ChatGPTAuthError(RuntimeError):
    """A deliberately sanitized error suitable for UI display and logs."""


class _CredentialStoreBusy(ChatGPTAuthError):
    pass


def _default_directory():
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "Soul-of-Waifu" / "ChatGPT"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "soul-of-waifu" / "chatgpt"


def _dpapi(data, decrypt=False):
    """DPAPI ties the encrypted file to the current Windows user's profile."""
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_char))]

    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    target = Blob()
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
        raise ChatGPTAuthError("Windows could not protect or unlock ChatGPT credentials.")
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        kernel.LocalFree(target.data)


class CredentialStore:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory is not None else _default_directory()
        self.path = self.directory / ("credentials.dpapi" if os.name == "nt" else "credentials.json")

    @contextmanager
    def locked(self, timeout=45):
        try:
            self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            if os.name != "nt":
                os.chmod(self.directory, 0o700)
            with FileLock(str(self.directory / "credentials.lock"), timeout=timeout):
                yield
        except Timeout:
            raise _CredentialStoreBusy("Another Soul of Waifu process is updating ChatGPT sign-in. Try again.") from None
        except OSError:
            raise ChatGPTAuthError("Cannot access the protected ChatGPT credential storage.") from None

    def read(self):
        if not self.path.exists():
            return {"version": 1, "host_id": "urn:uuid:" + str(uuid.uuid4()), "revision": 0, "active": None, "accounts": {}}
        try:
            raw = self.path.read_bytes()
            if os.name == "nt":
                raw = _dpapi(raw, decrypt=True)
            else:
                os.chmod(self.path, 0o600)
            data = json.loads(raw)
            if (not isinstance(data, dict) or data.get("version") != 1
                    or not isinstance(data.get("accounts"), dict)
                    or not isinstance(data.get("host_id"), str) or not data["host_id"]
                    or not isinstance(data.get("revision", 0), int) or data.get("revision", 0) < 0):
                raise ValueError()
            if data.get("active") is not None and data["active"] not in data["accounts"]:
                raise ValueError()
            for client_id, account in data["accounts"].items():
                if (not isinstance(account, dict) or account.get("client_id") != client_id
                        or client_id == DYNAMIC_CLIENT or not isinstance(account.get("subject"), str)
                        or not account["subject"] or account.get("issuer") != ISSUER
                        or not isinstance(account.get("scopes", []), list)
                        or any(not isinstance(scope, str) for scope in account.get("scopes", []))):
                    raise ValueError()
                for field in ("access_token", "refresh_token", "id_token", "email", "name"):
                    if field in account and not isinstance(account[field], str):
                        raise ValueError()
                expiry = account.get("expires_at", 0)
                if not isinstance(expiry, (int, float)) or not math.isfinite(expiry) or expiry < 0:
                    raise ValueError()
            return data
        except (ValueError, TypeError, OSError):
            raise ChatGPTAuthError("Cannot read ChatGPT credentials. Restore the protected account store or sign in from a new profile.") from None

    def write(self, data):
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        if os.name == "nt":
            raw = _dpapi(raw)
        temporary = None
        try:
            fd, temporary = tempfile.mkstemp(prefix=".credentials-", dir=self.directory)
            with os.fdopen(fd, "wb") as stream:
                if os.name != "nt":
                    os.fchmod(stream.fileno(), 0o600)
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)


class ChatGPTAuthManager:
    def __init__(self, store=None, session=None):
        self.store = store if store is not None else CredentialStore()
        self.session = session if session is not None else requests.Session()
        self._discovery_cache = None
        self._jwks_cache = None
        self._sign_in_lock = threading.Lock()

    @staticmethod
    def _public(account, active):
        return {"id": account["client_id"], "email": account.get("email", ""),
                "label": "%s (%s)" % (account.get("email") or account.get("name") or "ChatGPT account", account["client_id"][-8:]),
                "connected": bool(account.get("access_token") or account.get("id_token")),
                "plan_enabled": DIRECT_SCOPE in account.get("scopes", []),
                "active": account["client_id"] == active}

    def list_accounts(self):
        with self.store.locked():
            data = self.store.read()
            return [self._public(a, data["active"]) for a in data["accounts"].values()]

    def active_account(self):
        return next((a for a in self.list_accounts() if a["active"]), None)

    def try_list_accounts(self):
        """UI snapshot; None means retry later without blocking the event loop."""
        try:
            with self.store.locked(timeout=0):
                data = self.store.read()
                return [self._public(a, data["active"]) for a in data["accounts"].values()]
        except _CredentialStoreBusy:
            return None

    def set_active_account(self, account_id):
        with self.store.locked():
            data = self.store.read()
            if account_id not in data["accounts"]:
                raise ChatGPTAuthError("Choose a saved ChatGPT account first.")
            if data["active"] != account_id:
                data["active"] = account_id
                self._advance_revision(data)
                self.store.write(data)

    @staticmethod
    def _advance_revision(data):
        # A late browser callback must not undo a newer sign-out/account choice.
        data["revision"] = data.get("revision", 0) + 1

    @staticmethod
    def _check_cancelled(cancel_event):
        if cancel_event is not None and cancel_event.is_set():
            raise ChatGPTAuthError("ChatGPT sign-in was cancelled.")

    def _json_request(self, method, url, **kwargs):
        try:
            response = self.session.request(method, url, timeout=20, allow_redirects=False, **kwargs)
        except requests.RequestException:
            raise ChatGPTAuthError("Could not reach OpenAI sign-in. Check your connection and try again.") from None
        if response.status_code != 200:
            code = None
            try:
                error = response.json().get("error")
                code = error.get("code") if isinstance(error, dict) else error
            except (ValueError, AttributeError):
                pass
            if code in ("invalid_grant", "invalid_refresh_token", "token_expired", "refresh_token_expired",
                        "refresh_token_reused", "refresh_token_invalidated"):
                error = ChatGPTAuthError("ChatGPT sign-in expired or was revoked. Continue with ChatGPT again.")
                error.reauthorization_required = True
                raise error
            if code == "access_denied":
                raise ChatGPTAuthError("ChatGPT authorization was declined.")
            raise ChatGPTAuthError("OpenAI sign-in could not complete (HTTP %s). Try again." % response.status_code)
        try:
            result = response.json()
            if not isinstance(result, dict):
                raise ValueError()
            return result
        except ValueError:
            raise ChatGPTAuthError("OpenAI returned an invalid sign-in response.") from None

    @staticmethod
    def _trusted_url(url):
        try:
            parsed = urlsplit(url) if isinstance(url, str) else None
            trusted = (parsed and parsed.scheme == "https" and parsed.hostname == "auth.openai.com"
                       and parsed.port in (None, 443) and not parsed.username and not parsed.password and not parsed.fragment)
        except ValueError:
            trusted = False
        if not trusted:
            raise ChatGPTAuthError("OpenAI discovery returned an unexpected endpoint.")
        return url

    def _discovery(self):
        if self._discovery_cache is None:
            result = self._json_request("GET", ISSUER + "/.well-known/openid-configuration")
            if result.get("issuer") != ISSUER:
                raise ChatGPTAuthError("OpenAI sign-in issuer did not match.")
            self._trusted_url(result.get("jwks_uri"))
            self._discovery_cache = result
        return self._discovery_cache

    def _verify_identity(self, token, client_id, nonce=None):
        try:
            header = jwt.get_unverified_header(token)
            if header.get("alg") not in ("RS256", "ES256") or not header.get("kid"):
                raise ValueError()
            for attempt in range(2):
                if self._jwks_cache is None or time.time() - self._jwks_cache[0] > 3600 or attempt:
                    keys = self._json_request("GET", self._trusted_url(self._discovery()["jwks_uri"]))
                    self._jwks_cache = (time.time(), keys.get("keys", []))
                matches = [k for k in self._jwks_cache[1] if isinstance(k, dict) and k.get("kid") == header["kid"]]
                if matches:
                    break
            if len(matches) != 1:
                raise ValueError()
            key = jwt.PyJWK.from_dict(matches[0], algorithm=header["alg"])
            claims = jwt.decode(token, key.key, algorithms=[header["alg"]], audience=client_id,
                                issuer=ISSUER, leeway=5,
                                options={"require": ["iss", "aud", "sub", "exp", "iat"]})
            if not isinstance(claims.get("sub"), str) or not claims["sub"]:
                raise ValueError()
            if any(claims.get(field) is not None and not isinstance(claims[field], str) for field in ("email", "name")):
                raise ValueError()
            if claims.get("azp", client_id) != client_id:
                raise ValueError()
            if isinstance(claims["aud"], list) and len(claims["aud"]) > 1 and claims.get("azp") != client_id:
                raise ValueError()
            if nonce is not None and (not isinstance(claims.get("nonce"), str) or not secrets.compare_digest(claims["nonce"], nonce)):
                raise ValueError()
            return claims
        except (jwt.PyJWTError, ValueError, TypeError, KeyError):
            raise ChatGPTAuthError("ChatGPT account identity could not be verified. Start sign-in again.") from None

    @staticmethod
    def _apply_tokens(account, tokens, refreshing=False):
        try:
            scopes = tokens.get("scope")
            if scopes is None and refreshing:
                scopes = " ".join(account.get("scopes", []))
            if not isinstance(scopes, str):
                raise ValueError()
            access = tokens.get("access_token", "")
            if not access and DIRECT_SCOPE not in scopes.split() and not refreshing:
                account.update(access_token="", refresh_token="", scopes=scopes.split(), expires_at=0,
                               id_token=tokens["id_token"])
                return
            token_type = tokens.get("token_type", "")
            if not isinstance(access, str) or not access or not isinstance(token_type, str) or token_type.lower() != "bearer":
                raise ValueError()
            expiry = float(tokens["expires_in"])
            if not 0 < expiry <= 86400:
                raise ValueError()
            refresh = tokens.get("refresh_token")
            if "offline_access" in scopes.split() and not refresh:
                raise ValueError()
            if refreshing and account.get("refresh_token") and not refresh:
                raise ValueError()
            if refresh is not None and not isinstance(refresh, str):
                raise ValueError()
            account.update(access_token=access, refresh_token=refresh or "", scopes=scopes.split(),
                           expires_at=time.time() + expiry, token_type="Bearer")
            if tokens.get("id_token"):
                account["id_token"] = tokens["id_token"]
        except (ValueError, TypeError, KeyError):
            raise ChatGPTAuthError("OpenAI returned incomplete ChatGPT credentials. Sign in again.") from None

    def sign_in(self, account_id=None, cancel_event=None, open_browser=webbrowser.open, timeout=180):
        """Blocking browser login; call from a worker. Cancellation closes loopback."""
        if not self._sign_in_lock.acquire(blocking=False):
            raise ChatGPTAuthError("A ChatGPT sign-in is already in progress.")
        try:
            try:
                return self._sign_in(account_id, cancel_event, open_browser, timeout)
            except ChatGPTAuthError as error:
                issued_client_id = getattr(error, "issued_client_id", None)
                if not issued_client_id:
                    raise
                # A consumed/expired code must never be retried. Start a fresh
                # transaction, retaining the registration OpenAI just issued.
                return self._sign_in(account_id, cancel_event, open_browser, timeout,
                                     issued_client_id, error.expected_revision)
        finally:
            self._sign_in_lock.release()

    def _sign_in(self, account_id, cancel_event, open_browser, timeout,
                 issued_client_id=None, expected_revision=None):
        self._check_cancelled(cancel_event)
        with self.store.locked():
            data = self.store.read()
            if expected_revision is not None and data.get("revision", 0) != expected_revision:
                raise ChatGPTAuthError("ChatGPT account selection changed during sign-in. Start again if needed.")
            expected_revision = data.get("revision", 0)
            self.store.write(data)  # Persist this host before opening authorization.
            account = dict(data["accounts"].get(account_id, {})) if account_id else {}
            if account_id and not account:
                raise ChatGPTAuthError("The selected ChatGPT registration no longer exists.")
            if issued_client_id and not account:
                account = {"client_id": issued_client_id}
            host_id = data["host_id"]
        state, nonce, verifier = (secrets.token_urlsafe(32) for _ in range(3))
        result = {}

        class Callback(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass  # The request path includes an authorization code.

            def setup(self):
                self.request.settimeout(2)
                super().setup()

            def do_GET(self):
                try:
                    parsed = urlsplit(self.path)
                    query = parse_qs(parsed.query, keep_blank_values=True, max_num_fields=20)
                except ValueError:
                    query = {}
                    parsed = urlsplit("/")
                valid = (len(self.path) < 16384 and parsed.path == CALLBACK_PATH
                         and self.headers.get("Host") == "127.0.0.1:%s" % self.server.server_port
                         and len(query.get("state", [])) == 1
                         and secrets.compare_digest(query["state"][0].encode("utf-8"), state.encode("ascii"))
                         and all(len(values) == 1 for values in query.values()))
                self.send_response(200 if valid else 400)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Referrer-Policy", "no-referrer")
                self.end_headers()
                if valid:
                    result.update({key: value[0] for key, value in query.items()})
                try:
                    self.wfile.write(b"Return to Soul of Waifu to finish sign-in." if valid else b"Invalid sign-in callback.")
                except OSError:
                    pass

        try:
            server = HTTPServer(("127.0.0.1", 0), Callback)
        except OSError:
            raise ChatGPTAuthError("Cannot start the local ChatGPT sign-in callback. Check local firewall settings.") from None
        redirect = "http://127.0.0.1:%s%s" % (server.server_port, CALLBACK_PATH)
        params = dict(client_id=account.get("client_id", DYNAMIC_CLIENT), ext_agent_host_id=host_id,
                      response_type="code", redirect_uri=redirect, scope=SCOPES, resource=RESOURCE,
                      state=state, nonce=nonce, code_challenge_method="S256",
                      code_challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("="))
        if account:
            if account.get("id_token"):
                params["id_token_hint"] = account["id_token"]
            if account.get("email"):
                params["login_hint"] = account["email"]
            if account.get("id_token") and DIRECT_SCOPE not in account.get("scopes", []):
                # This is an explicit attempt to enable previously ungranted
                # plan usage; routine reauthorization does not force consent.
                params["prompt"] = "consent"
        else:
            params["agent_name_hint"] = "Soul of Waifu"
        try:
            try:
                opened = open_browser(AUTHORIZE_URL + "?" + urlencode(params))
            except Exception:
                raise ChatGPTAuthError("Could not open your browser for ChatGPT sign-in.") from None
            if opened is False:
                raise ChatGPTAuthError("Could not open your browser for ChatGPT sign-in.")
            deadline = time.monotonic() + timeout
            server.timeout = 0.25
            while not result:
                if cancel_event is not None and cancel_event.is_set():
                    raise ChatGPTAuthError("ChatGPT sign-in was cancelled.")
                if time.monotonic() >= deadline:
                    raise ChatGPTAuthError("ChatGPT sign-in timed out. Continue with ChatGPT again.")
                server.handle_request()
        finally:
            server.server_close()
        self._check_cancelled(cancel_event)
        if result.get("error"):
            raise ChatGPTAuthError("ChatGPT authorization was declined or could not complete.")
        client_id = result.get("client_id") or account.get("client_id")
        if not client_id or client_id == DYNAMIC_CLIENT or not result.get("code"):
            raise ChatGPTAuthError("ChatGPT registration did not return a client ID and authorization code.")
        if account and client_id != account["client_id"]:
            raise ChatGPTAuthError("ChatGPT returned a different account registration. Sign-in was rejected.")
        try:
            tokens = self._json_request("POST", TOKEN_URL, data=dict(grant_type="authorization_code",
                        client_id=client_id, code=result["code"], code_verifier=verifier, redirect_uri=redirect, resource=RESOURCE))
        except ChatGPTAuthError as error:
            if getattr(error, "reauthorization_required", False):
                error.issued_client_id = client_id
                error.expected_revision = expected_revision
            raise
        try:
            self._check_cancelled(cancel_event)
            claims = self._verify_identity(tokens.get("id_token"), client_id, nonce)
            if account.get("subject") and account["subject"] != claims["sub"]:
                raise ChatGPTAuthError("ChatGPT returned a different account. Your existing sign-in was preserved.")
            account.update(client_id=client_id, subject=claims["sub"], issuer=ISSUER,
                           email=claims.get("email") or "", name=claims.get("name") or "")
            self._apply_tokens(account, tokens)
            with self.store.locked():
                self._check_cancelled(cancel_event)
                data = self.store.read()
                if data.get("revision", 0) != expected_revision:
                    raise ChatGPTAuthError("ChatGPT account selection changed during sign-in. Your newer choice was preserved.")
                existing = data["accounts"].get(client_id)
                if existing and existing["subject"] != claims["sub"]:
                    raise ChatGPTAuthError("ChatGPT registration identity changed. Sign-in was rejected.")
                data["accounts"][client_id] = account
                data["active"] = client_id
                self._advance_revision(data)
                self.store.write(data)
        except ChatGPTAuthError as error:
            if not self._revoke_tokens(client_id, tokens):
                raise ChatGPTAuthError(str(error) + " Remote revocation was not confirmed; disconnect the unused session in ChatGPT Settings.") from None
            raise
        return self._public(account, client_id)

    def get_access_token(self, force_refresh=False, expected_account_id=None):
        with self.store.locked():
            data = self.store.read()
            if expected_account_id is not None and data["active"] != expected_account_id:
                raise ChatGPTAuthError("The active ChatGPT account changed. Start the request again.")
            account = data["accounts"].get(data["active"])
            if not account or not (account.get("access_token") or account.get("id_token")):
                raise ChatGPTAuthError("Continue with ChatGPT in Configuration to sign in first.")
            if DIRECT_SCOPE not in account.get("scopes", []):
                raise ChatGPTAuthError("ChatGPT plan usage is not enabled. Continue with ChatGPT to grant permission.")
            if force_refresh or account.get("expires_at", 0) <= time.time() + 60:
                if not account.get("refresh_token"):
                    raise ChatGPTAuthError("ChatGPT sign-in expired. Continue with ChatGPT again.")
                try:
                    tokens = self._json_request("POST", TOKEN_URL, data=dict(grant_type="refresh_token",
                             client_id=account["client_id"], refresh_token=account["refresh_token"], resource=RESOURCE))
                except ChatGPTAuthError as error:
                    if getattr(error, "reauthorization_required", False):
                        self._clear_tokens(account)
                        self._advance_revision(data)
                        self.store.write(data)
                    raise
                if tokens.get("id_token"):
                    claims = self._verify_identity(tokens["id_token"], account["client_id"])
                    if claims["sub"] != account["subject"]:
                        raise ChatGPTAuthError("ChatGPT refresh returned a different account. Sign in again.")
                self._apply_tokens(account, tokens, refreshing=True)
                self.store.write(data)
                if DIRECT_SCOPE not in account["scopes"]:
                    raise ChatGPTAuthError("ChatGPT plan permission was removed. Continue with ChatGPT again.")
            return account["access_token"]

    @staticmethod
    def _clear_tokens(account):
        for key in ("access_token", "refresh_token", "id_token", "expires_at"):
            account.pop(key, None)
        account["scopes"] = []

    def sign_out(self, account_id=None):
        """Clear local tokens in all cases; return whether revocation is confirmed."""
        with self.store.locked():
            data = self.store.read()
            account = data["accounts"].get(account_id or data["active"])
            if not account:
                self._advance_revision(data)
                self.store.write(data)
                return True
            try:
                confirmed = self._revoke_tokens(account["client_id"], account)
            finally:
                self._clear_tokens(account)
                self._advance_revision(data)
                self.store.write(data)
            return confirmed

    def _revoke_tokens(self, client_id, tokens):
        """Best-effort cleanup also covers abandoned, never-persisted logins."""
        refresh = tokens.get("refresh_token")
        if not isinstance(refresh, str) or not refresh:
            return not bool(tokens.get("access_token"))
        try:
            endpoint = self._trusted_url(self._discovery().get("revocation_endpoint"))
            for attempt in range(2):
                try:
                    response = self.session.request("POST", endpoint, timeout=10, allow_redirects=False,
                        data=dict(token=refresh, token_type_hint="refresh_token", client_id=client_id))
                    if response.status_code == 200:
                        return True
                    if response.status_code < 500:
                        return False
                except requests.RequestException:
                    pass
                if attempt == 0:
                    time.sleep(0.25)
        except ChatGPTAuthError:
            pass
        return False


_manager = None
_manager_lock = threading.Lock()


def get_chatgpt_auth():
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = ChatGPTAuthManager()
        return _manager
