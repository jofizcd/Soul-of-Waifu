import unittest
from pathlib import Path

import dev_sync


class DevSyncTest(unittest.TestCase):
    def test_sync_scope_excludes_runtime_state(self):
        self.assertTrue(dev_sync.is_syncable("main.py"))
        self.assertTrue(dev_sync.is_syncable("app/gui/interface_signals.py"))
        self.assertFalse(dev_sync.is_syncable("app/configuration/settings.json"))
        self.assertFalse(dev_sync.is_syncable("app/data/envs/sow/python.exe"))

    def test_parent_paths_are_rejected(self):
        with self.assertRaises(RuntimeError):
            dev_sync.safe_runtime_path(Path.cwd().resolve(), "../outside.txt")

    def test_help_does_not_sync(self):
        script = (Path(__file__).parents[1] / "run-dev.bat").read_text(encoding="utf-8")
        self.assertLess(script.index('"--help"'), script.index("dev_sync.py"))


if __name__ == "__main__":
    unittest.main()
