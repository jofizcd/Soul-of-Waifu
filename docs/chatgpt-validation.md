# ChatGPT connection validation

Validation date: 2026-10-13. Live requests used synthetic prompts and images on
Windows / Python 3.11. No account identifiers, credentials, or personal chats
are included in this repository.

All **145 focused tests passed** in a fresh environment with the CI dependency
set. Full application startup was also checked using the installed desktop runtime.

## Reproducible offline checks

The focused CI workflow installs only:

```console
python -m pip install "PyJWT[crypto]>=2.10.1,<3" filelock requests httpx openai==1.70.0 PyQt6==6.9.0 PyYAML==6.0.2
python -m unittest discover -s tests -p "test_chatgpt*.py" -v
```

Qt runs with `QT_QPA_PLATFORM=offscreen`. These tests do not need an account,
GPU models, microphones, or cloud credentials. OAuth callback tests use local
loopback sockets and generated signing keys. GUI flow tests execute complete
production handler methods with real Qt widgets and an in-memory chat store,
without importing unrelated speech/GPU startup modules. Soul Stage tests run its
production orchestration and parsers with fake provider streams.

## Evidence by scenario

| Scenario | Evidence |
| --- | --- |
| First browser sign-in, granted plan access, protected persistence | Live account connection succeeded; catalog returned seven eligible models. |
| Refresh and application restart | A separate process loaded DPAPI storage and successfully refreshed the live session. |
| Sign-out, revocation and returning sign-in | A separate live test registration completed sign-in, confirmed server revocation, local credential clearing, and returning sign-in with the same client registration. It was revoked again and its temporary protected store removed; the working session was preserved. |
| Text, streaming, multi-turn history | Live requests passed on `gpt-6.1-sol`. |
| Summary and memory | Live summary and the actual `PromptEngine._memory_llm_call` passed. Error and cancellation tests reject partial memory output. |
| Vision | A live request identified a synthetic red image. |
| Local tools | Live single- and two-function round trips passed, including full history replay. |
| Reasoning and existing caller parameters | Live default and medium reasoning passed; unsupported sampling/token fields are omitted. `none` means model default. |
| Main window and account settings | Full application startup, account widget, live model discovery and model persistence passed; API-key and unsupported sampling controls are hidden for ChatGPT. |
| Chat, Stop, regeneration and continuation | Complete handler tests check saved history, draft/attachment restoration, no partial memory update, Stop during streaming/commit and preservation of subsequent messages after failed regeneration. |
| Web client completion on failure | The existing end-of-message event is emitted on failure/cancellation; unavailable clients do not prevent local recovery. |
| Character creation | Real dialog tests cover successful JSON review, single-field regeneration, account readiness, and preservation of approved fields on error. |
| Soul Stage | Production orchestration tests cover planning, narration, NPC spawn/dialogue/routing, party-member dialogue, party memory, cancellation and stream failures. |
| Existing providers | Mock factory checks cover all twelve routes and OpenAI custom endpoint normalization. |
| Protocol and account failures | Tests cover PKCE/state/nonce/signatures/claims, refresh rotation, scope loss, concurrent sessions, HTTP failures, interrupted streams, refusal and late usage errors. |
| Completed stream cleanup | A completed response ends immediately. Real local chunked HTTP tests cover completion, consumer close and cancellation, including same-task transport cleanup; separately checked with Qt/qasync in the desktop runtime. |
| Chat tools streaming | Text deltas are displayed during each tool-enabled round. Delayed-terminal tests check early rendering, no tool execution before completion, repeated text chunks, multi-round output without duplication, Stop and partial failures. Tool results remain in context. Other providers retain their prior flow. |
| Message bubble transitions | Real Qt geometry tests cover populated send bubbles and composer sizing. A complete-handler regression reproduces the old empty bubble between Thinking and first text, and passes with the atomic replacement. |
| Current-news search | A live ChatGPT round trip invoked the existing web search twice and cited an official source, explicitly acknowledging when the requested publication period could not be verified. |

Live testing exposed two protocol differences now covered by regressions:
completed output items can arrive separately from an empty terminal response,
and the tested model rejects an explicit `reasoning.effort: "none"`.

A live Qt/qasync check of the tool-enabled chat stream on `gpt-6-astra` / medium
returned 47 text chunks in one request (first text 6.06 s, completion 7.74 s).
A harmless synthetic function round trip returned 38 text chunks in two requests
with exactly one local execution (first text 9.02 s, completion 10.78 s).
These are single-run measurements, not latency guarantees. The checks did not
write personal conversation history.

## Boundaries

- Live inference was checked on `gpt-6.1-sol` and a three-turn desktop conversation
  on `gpt-6-astra` with medium reasoning; availability and reasoning support
  vary by account and model. Other cloud providers were checked through their
  factory routes, without sending requests to paid external accounts.
- Microphone input, speech synthesis, voice conversion, avatars, and third-party
  MCP servers use existing independent engines; they are outside this connection's
  acceptance checks. The tool tests execute harmless local functions only.
- Web search returns result snippets and URLs; the live check does not establish
  the completeness of news coverage or verify every linked article in full.
- Soul Stage does not roll back an entire world plan on a later narrator error.
  Tests assert that incomplete narrator/NPC replies are not committed; prior
  completed actions and world-plan updates retain the existing behavior.
- Signing out prevents new requests, but an HTTP response already in progress
  must be stopped by its caller or allowed to complete. No external tool actions
  already performed can be undone by canceling a response.
- Linux/macOS packaging and real account/workspace switching across different
  identities require separate platform/account acceptance runs.
