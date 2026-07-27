import ast
import asyncio
import base64
import os
import tempfile
import unittest
import uuid
from pathlib import Path


ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "app/utils/text_to_speech.py"
TREE = ast.parse(SOURCE.read_text(encoding="utf-8"))
CLASS = next(node for node in TREE.body if isinstance(node, ast.ClassDef) and node.name == "InworldTTS")


def load_inworld_class():
    methods = [node for node in CLASS.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    module = ast.Module(body=[ast.ClassDef(name="InworldTTS", bases=[], keywords=[], body=methods, decorator_list=[])], type_ignores=[])
    namespace = {"aiohttp": None, "asyncio": asyncio, "base64": base64, "os": os, "uuid": uuid, "logger": None}
    exec(compile(ast.fix_missing_locations(module), str(SOURCE), "exec"), namespace)
    return namespace


class InworldTtsTest(unittest.IsolatedAsyncioTestCase):
    async def test_request_contract_and_wav_output(self):
        namespace = load_inworld_class()
        calls = {}

        class Response:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def json(self):
                return {"audioContent": base64.b64encode(b"RIFFtest").decode()}

        class Session:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            def post(self, url, **kwargs):
                calls["url"] = url
                calls.update(kwargs)
                return Response()

        class Aiohttp:
            ClientError = OSError

            @staticmethod
            def ClientTimeout(total):
                return total

            @staticmethod
            def ClientSession(timeout):
                calls["timeout"] = timeout
                return Session()

        namespace["aiohttp"] = Aiohttp
        namespace["logger"] = type("Logger", (), {"error": staticmethod(lambda *args: None)})()
        provider = namespace["InworldTTS"].__new__(namespace["InworldTTS"])
        provider.configuration_api = type("Api", (), {"get_token": lambda self, key: "secret-key"})()
        provider.configuration_characters = type("Characters", (), {"load_configuration": lambda self: {"character_list": {"Mio": {"inworld_voice_id": "Dennis", "inworld_model_id": "inworld-tts-2"}}}})()

        with tempfile.TemporaryDirectory() as directory:
            provider.output_dir = directory
            output = await provider.generate_speech_with_inworld("Hello", "Mio")
            self.assertEqual(Path(output).read_bytes(), b"RIFFtest")

        self.assertEqual(calls["url"], "https://api.inworld.ai/tts/v1/voice")
        self.assertEqual(calls["headers"]["Authorization"], "Basic secret-key")
        self.assertEqual(calls["json"], {
            "text": "Hello",
            "voiceId": "Dennis",
            "modelId": "inworld-tts-2",
            "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 22050},
        })


if __name__ == "__main__":
    unittest.main()
