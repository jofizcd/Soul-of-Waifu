import ast
import asyncio
import copy
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
INTERFACE_PATH = ROOT / "app/gui/interface_signals.py"
INTERFACE_TREE = ast.parse(INTERFACE_PATH.read_text(encoding="utf-8"))
INTERFACE_CLASS = next(
    node for node in INTERFACE_TREE.body
    if isinstance(node, ast.ClassDef) and node.name == "InterfaceSignals"
)


def method(name):
    return next(
        node for node in INTERFACE_CLASS.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    )


class OpenRouterModelsTest(unittest.IsolatedAsyncioTestCase):
    async def test_refresh_contract(self):
        fetch = method("fetch_openrouter_api_models")
        timeout = next(
            node for node in ast.walk(fetch)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "urlopen"
        )
        self.assertEqual(
            next(keyword.value.value for keyword in timeout.keywords if keyword.arg == "timeout"),
            15,
        )
        self.assertNotIn("Authorization", ast.unparse(fetch))

        module = ast.parse("import asyncio\nclass Controller:\n    pass\n")
        module.body[1].body = [copy.deepcopy(method("initialize_openrouter_models"))]
        namespace = {}
        exec(compile(ast.fix_missing_locations(module), INTERFACE_PATH, "exec"), namespace)
        controller = namespace["Controller"]()
        controller._openrouter_models_task = None

        started = asyncio.Event()
        release = asyncio.Event()
        calls = 0

        async def load_models():
            nonlocal calls
            calls += 1
            started.set()
            await release.wait()

        controller._load_and_populate_open_models = load_models
        controller.initialize_openrouter_models()
        first_task = controller._openrouter_models_task
        controller.initialize_openrouter_models()
        await started.wait()
        self.assertEqual(calls, 1)

        release.set()
        await first_task
        controller.initialize_openrouter_models()
        await controller._openrouter_models_task
        self.assertEqual(calls, 2)

        ui_source = (ROOT / "app/gui/sowInterface.py").read_text(encoding="utf-8")
        self.assertIn("openrouter_layout.addWidget(self.pushButton_reload_openrouter_models)", ui_source)


if __name__ == "__main__":
    unittest.main()
