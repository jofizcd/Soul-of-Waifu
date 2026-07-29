import ast
import datetime
import unittest
import uuid
from pathlib import Path


ROOT = Path(__file__).parents[1]
CONFIGURATION_SOURCE = ROOT / "app/configuration/configuration.py"
INTERFACE_SOURCE = ROOT / "app/gui/interface_signals.py"


def load_method(source, class_name, method_name, namespace):
    tree = ast.parse(source.read_text(encoding="utf-8"))
    source_class = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    method = next(
        node for node in source_class.body
        if isinstance(node, ast.FunctionDef) and node.name == method_name
    )
    module = ast.Module(
        body=[ast.ClassDef(
            name=class_name,
            bases=[],
            keywords=[],
            body=[method],
            decorator_list=[],
        )],
        type_ignores=[],
    )
    exec(compile(ast.fix_missing_locations(module), str(source), "exec"), namespace)
    return namespace[class_name]


class CharacterModelOverrideTest(unittest.TestCase):
    def test_saved_override_reaches_provider_factory(self):
        configuration = CONFIGURATION_SOURCE.read_text(encoding="utf-8")
        self.assertIn('"model_override": model_override or None', configuration)

        factory = ast.parse((ROOT / "app/utils/ai_clients/ai_factory.py").read_text(encoding="utf-8"))
        get_provider = next(
            node for node in ast.walk(factory)
            if isinstance(node, ast.FunctionDef) and node.name == "get_provider"
        )
        self.assertIn("model_override", [arg.arg for arg in get_provider.args.args])

        interface = INTERFACE_SOURCE.read_text(encoding="utf-8")
        self.assertIn('AIFactory.get_provider(conversation_method, character_info.get("model_override"))', interface)

    def test_openrouter_override_uses_model_id(self):
        interface_signals = load_method(
            INTERFACE_SOURCE,
            "InterfaceSignals",
            "_editor_model_override",
            {},
        )

        class Combo:
            def currentData(self):
                return "openai/gpt-4.1"

            def currentText(self):
                return "GPT-4.1"

        editor = interface_signals()
        editor.ui = type("Ui", (), {"comboBox_character_model_override": Combo()})()
        self.assertEqual(editor._editor_model_override(), "openai/gpt-4.1")

    def test_new_character_fields_are_saved(self):
        configuration = load_method(
            CONFIGURATION_SOURCE,
            "ConfigurationCharacters",
            "save_character_card",
            {"datetime": datetime, "uuid": uuid},
        )
        saved = {}
        characters = configuration()
        characters.load_configuration = lambda: {"character_list": {}}
        characters.save_configuration_edit = lambda data: saved.update(data)

        characters.save_character_card(
            "Mio", "", "", "Description", "Kind", "Hello", "", "", [],
            "", "", "", "", "", False, "", "", "", "", "OpenRouter",
            model_override="openai/gpt-4.1",
            selected_lorebooks=["world.json"],
            sow_variables=["mood"],
        )

        character = saved["character_list"]["Mio"]
        self.assertEqual(character["model_override"], "openai/gpt-4.1")
        self.assertEqual(character["selected_lorebooks"], ["world.json"])
        self.assertEqual(character["sow_variables"], ["mood"])


if __name__ == "__main__":
    unittest.main()
