# ChatGPT account connection

Soul of Waifu can use eligible models through **Sign in with ChatGPT**, without
an OpenAI API key or a separate Codex installation. The existing OpenAI/custom
endpoint provider continues to use its own configuration.

## Connect

1. Install the dependencies with `installer.bat`. Existing installations also
   need `PyJWT[crypto]>=2.10.1,<3` and `filelock` in the application's Python environment.
2. Open **Options → Configuration** and select **ChatGPT**.
3. Choose **Continue with ChatGPT**. Sign in and review the permissions in your
   system browser. The callback returns to a temporary listener on `127.0.0.1`.
4. Allow ChatGPT plan usage if offered. Identity-only sign-in does not enable
   model requests. Eligibility and available models depend on the account and workspace.
5. Refresh the model list and select a model available to that account.
6. Select **ChatGPT** as the conversation provider for a character or Soul Stage scene.

Text generation, character creation, summaries/memory, and supported local tool
requests use the selected ChatGPT account. Background memory work also consumes
its usage allowance. Manage access and limits in
[ChatGPT Settings → Usage](https://chatgpt.com/settings/usage).

Speech recognition and speech synthesis still use Soul of Waifu's separate
voice engines. This connection does not add ChatGPT audio, image generation,
hosted connectors, or access to existing ChatGPT conversations.

## Accounts and credentials

Use the account picker to select a saved registration or add another account.
Reconnecting keeps that registration and its workspace. A successful connection
is required before a new registration replaces the active account.

Credentials are kept in the app's per-user credential storage, outside the
installation and its backups. Windows protects the credential file with DPAPI;
Unix uses owner-only permissions. Access tokens, refresh tokens and retained ID
tokens must never be pasted into the normal API-key field, committed, or shared.
Moving the portable installation does not transfer the ChatGPT connection.

Sign out attempts to revoke the renewable session and clears local credentials.
If remote revocation cannot be confirmed, disconnect the app in ChatGPT settings.
An already-running response can continue until stopped or completed; use the
chat's Stop button to cancel it. Switching accounts affects subsequent requests;
an authorization retry never silently moves a request to another account.

## Protocol and limitations

This provider uses the documented public `https://api.openai.com/v1/responses`
endpoint with OAuth bearer authorization, `store: false`, and `stream: true`.
It sends the required conversation history on each request. It does not read
Codex credentials or call undocumented ChatGPT backend endpoints.

ChatGPT plan usage currently does not accept the usual temperature, top-p and
maximum-output-token settings; the provider omits those fields. Reasoning effort
is model-dependent; selecting `none` leaves the model's default reasoning behavior.
Local function tools are mapped to Responses namespaces;
execution remains in Soul of Waifu and retains its existing approval rules.

A response is successful only after `response.completed`. Account access and
usage errors can arrive after text has started streaming. Signing in and listing
models alone do not establish that generation will succeed.

## Development checks

Run the focused tests from the repository root:

```console
python -m unittest discover -s tests -p "test_chatgpt*.py"
```

Tests use fake credentials and mocked HTTP responses. A real-account acceptance
check requires browser consent: connect, select a returned model, complete a
short chat, run a summary, exercise a harmless tool round-trip, restart the app,
and sign out. Report live checks separately from mocked tests.

See the [validation matrix](chatgpt-validation.md) for tested scenarios and limits.

## Official references

- [Registration and sign-in](https://developers.openai.com/siwc/token-sharing-open-source/sign-in)
- [Accounts and sessions](https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions)
- [Models and inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
- [Preview limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)
