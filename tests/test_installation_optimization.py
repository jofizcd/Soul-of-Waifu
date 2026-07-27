import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.utils.character_cards import CHUB_HEADERS, CharactersCard


ROOT = Path(__file__).resolve().parents[1]


class CharacterCardsTest(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_json_uses_existing_http_client(self):
        response = MagicMock()
        response.status = 200
        response.text = AsyncMock(return_value='{"nodes": [{"name": "Test"}]}')
        response.__aenter__ = AsyncMock(return_value=response)
        response.__aexit__ = AsyncMock(return_value=None)

        session = MagicMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        session.get.return_value = response

        with patch(
            "app.utils.character_cards.aiohttp.ClientSession",
            return_value=session,
        ) as client_session:
            result = await CharactersCard.__new__(CharactersCard)._fetch_json(
                "https://gateway.chub.ai/search"
            )

        self.assertEqual(result, {"nodes": [{"name": "Test"}]})
        self.assertEqual(client_session.call_args.kwargs["headers"], CHUB_HEADERS)
        self.assertEqual(client_session.call_args.kwargs["timeout"].total, 30)
        session.get.assert_called_once_with("https://gateway.chub.ai/search")


class InstallationManifestTest(unittest.TestCase):
    def test_removed_dependencies_are_not_installed(self):
        removed = {
            "asttokens",
            "beautifulsoup4",
            "davey",
            "executing",
            "greenlet",
            "ipython",
            "ipython-pygments-lexers",
            "jedi",
            "matplotlib-inline",
            "parso",
            "playwright",
            "prompt-toolkit",
            "pure-eval",
            "pyee",
            "pynacl",
            "stack-data",
            "traitlets",
            "wcwidth",
        }
        requirements = {
            line.split("==", 1)[0].strip().lower().replace("_", "-")
            for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
            if "==" in line
        }
        installer = (ROOT / "installer.bat").read_text(encoding="utf-8").lower()

        self.assertTrue(removed.isdisjoint(requirements))
        for package in {"beautifulsoup4", "davey", "ipython", "playwright", "pynacl"}:
            self.assertNotIn(package, installer)


if __name__ == "__main__":
    unittest.main()
