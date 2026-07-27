import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class CharacterModelOverrideTest(unittest.TestCase):
    def test_saved_override_reaches_provider_factory(self):
        configuration = (ROOT / "app/configuration/configuration.py").read_text(encoding="utf-8")
        self.assertIn('"model_override": model_override or None', configuration)

        factory = ast.parse((ROOT / "app/utils/ai_clients/ai_factory.py").read_text(encoding="utf-8"))
        get_provider = next(
            node for node in ast.walk(factory)
            if isinstance(node, ast.FunctionDef) and node.name == "get_provider"
        )
        self.assertIn("model_override", [arg.arg for arg in get_provider.args.args])

        interface = (ROOT / "app/gui/interface_signals.py").read_text(encoding="utf-8")
        self.assertIn('AIFactory.get_provider(conversation_method, character_info.get("model_override"))', interface)


if __name__ == "__main__":
    unittest.main()
