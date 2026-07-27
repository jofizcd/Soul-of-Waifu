import logging
import json
import base64
import aiohttp
from PIL import Image

from app.configuration import configuration

logger = logging.getLogger("Characters Card Client")
CHUB_HEADERS = {
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    ),
}


class CharactersCard():
    def __init__(self):
        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_characters = configuration.ConfigurationCharacters()

    async def _fetch_json(self, url):
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(headers=CHUB_HEADERS, timeout=timeout) as session:
                async with session.get(url) as response:
                    text = await response.text()
                    if 'Attention Required!' in text or 'Just a moment...' in text:
                        logger.error("Blocked by Cloudflare")
                        return None
                    if response.status != 200:
                        logger.error(f"HTTP Error {response.status}: {text}")
                        return None
                    return json.loads(text)
        except Exception as e:
            logger.error(f"Chub API request failed: {e}")
            return None

    async def fetch_trending_character_data(self):
        self.nsfw_query = self.configuration_settings.get_main_setting("nsfw_query")
        if self.nsfw_query:
            url = "https://gateway.chub.ai/search?first=50&page=1&namespace=characters&nsfw=true&nsfw_only=false&nsfl=false&min_tokens=100&max_tokens=100000&chub=true&sort=trending&venus=true&count=false"
        else:
            url = "https://gateway.chub.ai/search?first=50&page=1&namespace=characters&nsfw=false&nsfw_only=false&nsfl=false&min_tokens=100&max_tokens=100000&chub=true&sort=trending&venus=true&count=false"
        return await self._fetch_json(url)

    async def search_character(self, character_name):
        self.nsfw_query = self.configuration_settings.get_main_setting("nsfw_query")
        if self.nsfw_query:
            url = f"https://gateway.chub.ai/search?first=50&page=1&namespace=characters&search={character_name}&include_forks=true&nsfw=true&nsfw_only=false&nsfl=false&asc=false&min_ai_rating=0&min_tokens=100&max_tokens=100000&chub=true&exclude_mine=true&sort=default&topics=&inclusive_or=false&recommended_verified=false&venus=true&count=false"
        else:
            url = f"https://gateway.chub.ai/search?excludetopics=NSFW&first=50&page=1&namespace=characters&search={character_name}&include_forks=true&nsfw=false&nsfw_only=false&nsfl=false&asc=false&min_ai_rating=0&min_tokens=100&max_tokens=100000&chub=true&exclude_mine=true&sort=default&topics=&inclusive_or=false&recommended_verified=false&venus=true&count=false"

        return await self._fetch_json(url)

    async def get_character_information(self, full_path):
        url = f"https://gateway.chub.ai/api/characters/{full_path}?full=true&nocache=0.6411485396222347"
        data = await self._fetch_json(url)
        if not data:
            return self._default_character_data()

        try:
            node = data.get("node")
            if not node:
                return self._default_character_data()

            return (
                node.get('name', 'Unknown'),
                node.get('tagline', 'No tagline'),
                node.get('avatar_url', 'No avatar'),
                node.get('starCount', 0),
                node.get('n_favorites', 0),
                node.get('nTokens', 0),
                node.get('definition', {}).get('personality', ''),
                node.get('definition', {}).get('first_message', ''),
                node.get('definition', {}).get('tavern_personality', ''),
                node.get('definition', {}).get('example_dialogs', ''),
                node.get('definition', {}).get('scenario', ''),
                node.get('definition', {}).get('alternate_greetings', [])
            )
        except Exception as e:
            logger.error(f"Error getting character info: {e}")
            return self._default_character_data()

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
    
class SoulGateway():
    def __init__(self):
        super().__init__()
        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_characters = configuration.ConfigurationCharacters()
    
    def read_v2_card(self, path):
        try:
            image = Image.open(path)
            user_comment = image.text.get('chara', None)
            if user_comment is None:
                return None
            json_bytes = base64.b64decode(user_comment)
            return json.loads(json_bytes.decode('utf-8'))
        except Exception as e:
            logger.error(f"Error decoding V2 card: {e}")
            return None
