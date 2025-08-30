import logging
from playwright.async_api import async_playwright

from app.configuration import configuration

logger = logging.getLogger("Characters Card Client")

class CharactersCard():
    def __init__(self):
        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_characters = configuration.ConfigurationCharacters()

    async def fetch_trending_character_data(self):
        self.nsfw_query = self.configuration_settings.get_main_setting("nsfw_query")
        if self.nsfw_query:
            url = "https://gateway.chub.ai/search?first=50&page=1&namespace=characters&nsfw=true&nsfw_only=false&nsfl=false&min_tokens=100&max_tokens=100000&chub=true&sort=trending&venus=true&count=false "
        else:
            url = "https://gateway.chub.ai/search?first=50&page=1&namespace=characters&nsfw=false&nsfw_only=false&nsfl=false&min_tokens=100&max_tokens=100000&chub=true&sort=trending&venus=true&count=false "

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                response = await page.goto(url, wait_until="networkidle")
                text = await response.text()

                if 'Attention Required!' in text or 'Just a moment...' in text:
                    logger.error("Blocked by Cloudflare")
                    return None

                if response.status != 200:
                    logger.error(f"HTTP Error {response.status}: {text}")
                    return None

                data = await page.evaluate("() => JSON.parse(document.body.innerText)")
                await browser.close()
                return data

            except Exception as e:
                logger.error(f"Error fetching trending characters: {e}")
                return None
            finally:
                await browser.close()

    async def search_character(self, character_name):
        self.nsfw_query = self.configuration_settings.get_main_setting("nsfw_query")
        if self.nsfw_query:
            url = f"https://gateway.chub.ai/search?first=50&page=1&namespace=characters&search={character_name}&include_forks=true&nsfw=true&nsfw_only=false&nsfl=false&asc=false&min_ai_rating=0&min_tokens=100&max_tokens=100000&chub=true&exclude_mine=true&sort=default&topics=&inclusive_or=false&recommended_verified=false&venus=true&count=false"
        else:
            url = f"https://gateway.chub.ai/search?excludetopics=NSFW&first=50&page=1&namespace=characters&search={character_name}&include_forks=true&nsfw=false&nsfw_only=false&nsfl=false&asc=false&min_ai_rating=0&min_tokens=100&max_tokens=100000&chub=true&exclude_mine=true&sort=default&topics=&inclusive_or=false&recommended_verified=false&venus=true&count=false"

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                response = await page.goto(url, wait_until="networkidle")
                text = await response.text()

                if 'Attention Required!' in text or 'Just a moment...' in text:
                    logger.error("Blocked by Cloudflare")
                    return None

                if response.status != 200:
                    logger.error(f"HTTP Error {response.status}: {text}")
                    return None

                data = await page.evaluate("() => JSON.parse(document.body.innerText)")
                await browser.close()
                return data

            except Exception as e:
                logger.error(f"Error fetching trending characters: {e}")
                return None
            finally:
                await browser.close()

    async def get_character_information(self, full_path):
        url = f"https://gateway.chub.ai/api/characters/{full_path}?full=true&nocache=0.6411485396222347"

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                response = await page.goto(url, wait_until="networkidle")
                text = await response.text()

                if 'Attention Required!' in text or 'Just a moment...' in text:
                    logger.error("Blocked by Cloudflare")
                    return self._default_character_data()

                if response.status != 200:
                    logger.error(f"HTTP Error {response.status}: {text}")
                    return self._default_character_data()

                try:
                    data = await page.evaluate("() => JSON.parse(document.body.innerText)")
                    await browser.close()
                except Exception as e:
                    logger.error("Failed to parse JSON:", text)
                    return self._default_character_data()

                node = data.get("node")
                if node:
                    character_name = node.get('name', 'Unknown')
                    character_title = node.get('tagline', 'No tagline')
                    character_avatar_url = node.get('avatar_url', 'No avatar')
                    downloads = node.get('starCount', 0)
                    likes = node.get('n_favorites', 0)
                    total_tokens = node.get('nTokens', 0)
                    character_personality = node.get('definition', {}).get('personality', '')
                    character_tavern_personality = node.get('definition', {}).get('tavern_personality', '')
                    example_dialogs = node.get('definition', {}).get('example_dialogs', '')
                    character_scenario = node.get('definition', {}).get('scenario', '')
                    alternate_greetings = node.get('definition', {}).get('alternate_greetings', [])
                    first_message = node.get('definition', {}).get('first_message', '')

                    return (
                        character_name,
                        character_title,
                        character_avatar_url,
                        downloads,
                        likes,
                        total_tokens,
                        character_personality,
                        first_message,
                        character_tavern_personality,
                        example_dialogs,
                        character_scenario,
                        alternate_greetings
                    )
                else:
                    return self._default_character_data()
            except Exception as e:
                logger.error(f"Error getting character info: {e}")
                return self._default_character_data()
            finally:
                await browser.close()

    def _default_character_data(self):
        return (
            'Unknown',                # character_name
            'No tagline',             # character_title
            'No avatar',              # character_avatar_url
            0,                        # downloads
            0,                        # likes
            0,                        # total_tokens
            'No description',         # character_personality
            'No first message',       # first_message
            None,                     # character_tavern_personality
            [],                       # example_dialogs
            'No scenario',            # character_scenario
            []                        # alternate_greetings
        )