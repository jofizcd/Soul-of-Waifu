import ast
import asyncio
import base64
import os
import tempfile
import unittest
import uuid
import wave
from pathlib import Path


ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "app/utils/text_to_speech.py"
TREE = ast.parse(SOURCE.read_text(encoding="utf-8"))
CLASS = next(node for node in TREE.body if isinstance(node, ast.ClassDef) and node.name == "InworldTTS")
SIGNALS = ast.parse((ROOT / "app/gui/interface_signals.py").read_text(encoding="utf-8"))
SIGNALS_CLASS = next(node for node in SIGNALS.body if isinstance(node, ast.ClassDef) and node.name == "InterfaceSignals")


def load_inworld_class():
    methods = [node for node in CLASS.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    module = ast.Module(body=[ast.ClassDef(name="InworldTTS", bases=[], keywords=[], body=methods, decorator_list=[])], type_ignores=[])
    namespace = {"aiohttp": None, "asyncio": asyncio, "base64": base64, "os": os, "uuid": uuid, "wave": wave, "logger": None, "sow_toast": lambda **kwargs: None}
    exec(compile(ast.fix_missing_locations(module), str(SOURCE), "exec"), namespace)
    return namespace


def load_clone_methods():
    names = {"clone_global_inworld_voice"}
    methods = [node for node in SIGNALS_CLASS.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names]
    module = ast.Module(body=[ast.ClassDef(name="InterfaceSignals", bases=[], keywords=[], body=methods, decorator_list=[])], type_ignores=[])
    namespace = {"aiohttp": None, "asyncio": asyncio, "base64": base64, "os": os, "wave": wave, "sow_toast": lambda **kwargs: None}
    exec(compile(ast.fix_missing_locations(module), "interface_signals.py", "exec"), namespace)
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

    async def test_clone_request_contract(self):
        namespace = load_clone_methods()
        calls = {}

        class Response:
            status = 201
            async def __aenter__(self): return self
            async def __aexit__(self, *args): return False
            async def json(self): return {"voiceId": "new-voice"}

        class Session:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): return False
            def post(self, url, **kwargs):
                calls["url"] = url
                calls.update(kwargs)
                return Response()

        namespace["aiohttp"] = type("Aiohttp", (), {
            "ClientError": OSError,
            "ClientTimeout": staticmethod(lambda total: total),
            "ClientSession": staticmethod(lambda timeout: Session()),
        })
        provider = namespace["InterfaceSignals"].__new__(namespace["InterfaceSignals"])
        provider.main_window = None

        class Text:
            def __init__(self, value): self.value = value
            def text(self): return self.value
        class Checked:
            def isChecked(self): return True
        class Combo:
            def currentText(self): return "RU_RU"
        class VoiceCombo:
            def findData(self, value): return 0 if value == "new-voice" else -1
            def setCurrentIndex(self, index): calls["selected"] = index

        with tempfile.TemporaryDirectory() as directory:
            sample = Path(directory) / "sample.wav"
            with wave.open(str(sample), "wb") as wav_file:
                wav_file.setnchannels(1); wav_file.setsampwidth(2); wav_file.setframerate(8000)
                wav_file.writeframes(b"\0\0" * 8000 * 5)
            provider.ui = type("Ui", (), {
                "lineEdit_tts_inworld_clone_file": Text(str(sample)),
                "lineEdit_tts_inworld_clone_name": Text("My voice"),
                "checkBox_tts_inworld_clone_rights": Checked(),
                "comboBox_tts_inworld_clone_language": Combo(),
                "comboBox_tts_inworld_voice": VoiceCombo(),
            })()
            provider.translations = {}
            provider._global_inworld_api_key = lambda: "secret-key"
            provider.load_global_inworld_voices = lambda: asyncio.sleep(0)
            await provider.clone_global_inworld_voice()

        self.assertEqual(calls["url"], "https://api.inworld.ai/voices/v1/voices:clone")
        self.assertEqual(calls["headers"]["Authorization"], "Basic secret-key")
        self.assertEqual(calls["json"]["langCode"], "RU_RU")
        self.assertTrue(calls["json"]["audioProcessingConfig"]["removeBackgroundNoise"])
        self.assertEqual(calls["selected"], 0)


if __name__ == "__main__":
    unittest.main()
