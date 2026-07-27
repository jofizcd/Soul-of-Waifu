import json
import tempfile
import unittest
from pathlib import Path

from app.configuration.configuration import ConfigurationSettings


class TtsProviderSettingsTest(unittest.TestCase):
    def test_inworld_global_defaults_are_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = ConfigurationSettings()
            settings.settings_path = str(Path(tmp) / "settings.json")
            settings.update_main_setting(
                "tts_providers",
                {"Inworld": {"enabled": True, "default_voice_id": "Dennis", "default_model_id": "inworld-tts-2"}},
            )
            data = json.loads(Path(settings.settings_path).read_text(encoding="utf-8"))
            self.assertEqual(data["main_settings"]["tts_providers"]["Inworld"]["default_model_id"], "inworld-tts-2")


if __name__ == "__main__":
    unittest.main()
