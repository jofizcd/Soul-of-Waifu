import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class UiResponsivenessContractTest(unittest.TestCase):
    def test_blocking_work_runs_outside_gui_thread(self):
        main = (ROOT / "main.py").read_text(encoding="utf-8")
        system = (ROOT / "app/gui/sow_system_signals.py").read_text(encoding="utf-8")

        self.assertIn("latest_version, github_url = await asyncio.to_thread(", main)
        self.assertIn(
            "self.tokenizer, self.session = await asyncio.to_thread(_load_model)",
            system,
        )
        self.assertIn(
            "predicted_class_id = await asyncio.to_thread(_run_inference)",
            system,
        )

    def test_gateway_reuses_recent_cards(self):
        interface = (ROOT / "app/gui/interface_signals.py").read_text(encoding="utf-8")

        self.assertIn("GATEWAY_CACHE_TTL_SECONDS = 300", interface)
        self.assertIn("def _gateway_tab_is_cached(self, tab, cards):", interface)
        self.assertIn("time.monotonic() - self._gateway_tab_loaded_at.get(tab, 0)", interface)


if __name__ == "__main__":
    unittest.main()
