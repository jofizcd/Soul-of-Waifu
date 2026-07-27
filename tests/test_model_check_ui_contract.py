import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SIGNALS = ast.parse((ROOT / "app/gui/interface_signals.py").read_text(encoding="utf-8"))


def method(name):
    cls = next(node for node in SIGNALS.body if isinstance(node, ast.ClassDef) and node.name == "InterfaceSignals")
    return next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == name)


class ModelCheckUiContractTest(unittest.TestCase):
    def test_changed_provider_settings_reset_the_model_check_result(self):
        for name in (
            "on_comboBox_conversation_method_changed",
            "_save_model_setting",
            "save_api_token_in_real_time",
            "save_custom_url_in_real_time",
        ):
            self.assertIn("_reset_model_test_result", ast.unparse(method(name)))

        reset = ast.unparse(method("_reset_model_test_result"))
        self.assertIn("label_model_test_result.clear()", reset)
        self.assertIn("_model_test_task.cancel()", reset)


if __name__ == "__main__":
    unittest.main()
