import ast
import asyncio
import base64
import unittest
from pathlib import Path


SOURCE = Path(__file__).parents[1] / "app/gui/interface_signals.py"
TREE = ast.parse(SOURCE.read_text(encoding="utf-8"))
INTERFACE = next(node for node in TREE.body if isinstance(node, ast.ClassDef) and node.name == "InterfaceSignals")


def load_api_methods():
    methods = [node for node in INTERFACE.body if isinstance(node, ast.AsyncFunctionDef) and node.name in {"fetch_inworld_voices", "preview_inworld_voice"}]
    module = ast.Module(body=[ast.ClassDef(name="InterfaceSignals", bases=[], keywords=[], body=methods, decorator_list=[])], type_ignores=[])
    namespace = {"aiohttp": None, "base64": base64, "logger": None}
    exec(compile(ast.fix_missing_locations(module), str(SOURCE), "exec"), namespace)
    return namespace


class InworldVoiceApiTest(unittest.IsolatedAsyncioTestCase):
    async def test_voice_list_and_preview_contract(self):
        namespace = load_api_methods()
        calls = []

        class Response:
            status = 200
            def __init__(self, data): self.data = data
            async def __aenter__(self): return self
            async def __aexit__(self, *args): return False
            async def json(self): return self.data

        class Session:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): return False
            def get(self, url, **kwargs):
                calls.append((url, kwargs))
                if url.endswith("/voices"):
                    return Response({"voices": [{"displayName": "Ashley", "voiceId": "ashley-id"}]})
                return Response({"audioContent": base64.b64encode(b"ID3preview").decode()})

        class Aiohttp:
            ClientError = OSError
            ClientTimeout = staticmethod(lambda total: total)
            ClientSession = staticmethod(lambda timeout: Session())

        namespace["aiohttp"] = Aiohttp
        namespace["logger"] = type("Logger", (), {"error": staticmethod(lambda *args: None)})()
        client = namespace["InterfaceSignals"]()
        self.assertEqual(await client.fetch_inworld_voices("secret-key"), [("Ashley", "ashley-id")])
        self.assertEqual(await client.preview_inworld_voice("secret-key", "ashley-id", "inworld-tts-2"), b"ID3preview")
        self.assertEqual(calls[0][0], "https://api.inworld.ai/voices/v1/voices")
        self.assertEqual(calls[0][1]["headers"]["Authorization"], "Basic secret-key")
        self.assertEqual(calls[1][1]["params"], {"voice_id": "ashley-id", "model_id": "inworld-tts-2"})


if __name__ == "__main__":
    unittest.main()
