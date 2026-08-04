import asyncio
import base64
import json
import logging
import time
from typing import Any, Optional

from PIL import Image
from curl_cffi.requests import AsyncSession

from app.configuration import configuration

logger = logging.getLogger("Characters Card Client")

IMPERSONATE = "chrome124"

DEFAULT_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

CLOUDFLARE_MARKERS = ("Attention Required!", "Just a moment...")


class _TTLCache:

    def __init__(self, ttl_seconds: int = 60):
        self.ttl = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str):
        item = self._store.get(key)
        if not item:
            return None
        expires_at, value = item
        if time.monotonic() > expires_at:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any):
        self._store[key] = (time.monotonic() + self.ttl, value)


class CharactersCard:
    _session: Optional[AsyncSession] = None
    _session_lock = asyncio.Lock()

    _trending_cache = _TTLCache(ttl_seconds=60)
    _search_cache = _TTLCache(ttl_seconds=30)
    _info_cache = _TTLCache(ttl_seconds=300)

    def __init__(self):
        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_characters = configuration.ConfigurationCharacters()

    @classmethod
    async def _get_session(cls) -> AsyncSession:
        if cls._session is None:
            async with cls._session_lock:
                if cls._session is None:
                    cls._session = AsyncSession(
                        headers=DEFAULT_HEADERS,
                        timeout=20,
                    )
        return cls._session

    @classmethod
    async def close(cls):
        if cls._session is not None:
            await cls._session.close()
            cls._session = None

    async def _get_json(self, url: str, retries: int = 2) -> Optional[dict]:
        session = await self._get_session()

        last_error = None
        for attempt in range(retries + 1):
            try:
                response = await session.get(url, impersonate=IMPERSONATE)
                text = response.text

                if any(marker in text for marker in CLOUDFLARE_MARKERS):
                    logger.warning(
                        "Cloudflare challenge detected (attempt %s/%s): %s",
                        attempt + 1, retries + 1, url,
                    )
                    last_error = "cloudflare_challenge"
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue

                if response.status_code != 200:
                    logger.error(
                        "HTTP Error %s for %s: %s",
                        response.status_code, url, text[:300],
                    )
                    last_error = f"http_{response.status_code}"
                    continue

                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    logger.error("Failed to parse JSON from %s: %s", url, text[:300])
                    return None

            except Exception as e:
                logger.error("Request error for %s: %s", url, e)
                last_error = str(e)
                await asyncio.sleep(0.5 * (attempt + 1))

        logger.error("Giving up on %s after %s attempts (%s)", url, retries + 1, last_error)
        return None

    def _nsfw_flag(self) -> bool:
        return bool(self.configuration_settings.get_main_setting("nsfw_query"))

    async def fetch_trending_character_data(self):
        nsfw = self._nsfw_flag()
        cache_key = f"trending:{nsfw}"
        cached = self._trending_cache.get(cache_key)
        if cached is not None:
            return cached

        url = (
            "https://gateway.chub.ai/search?first=50&page=1&namespace=characters"
            f"&nsfw={'true' if nsfw else 'false'}&nsfw_only=false&nsfl=false"
            "&min_tokens=100&max_tokens=100000&chub=true&sort=trending&venus=true&count=false"
        )

        data = await self._get_json(url)
        if data is not None:
            self._trending_cache.set(cache_key, data)
        return data

    async def search_character(self, character_name: str):
        nsfw = self._nsfw_flag()
        cache_key = f"search:{nsfw}:{character_name}"
        cached = self._search_cache.get(cache_key)
        if cached is not None:
            return cached

        if nsfw:
            url = (
                "https://gateway.chub.ai/search?first=50&page=1&namespace=characters"
                f"&search={character_name}&include_forks=true&nsfw=true&nsfw_only=false"
                "&nsfl=false&asc=false&min_ai_rating=0&min_tokens=100&max_tokens=100000"
                "&chub=true&exclude_mine=true&sort=default&topics=&inclusive_or=false"
                "&recommended_verified=false&venus=true&count=false"
            )
        else:
            url = (
                "https://gateway.chub.ai/search?excludetopics=NSFW&first=50&page=1"
                f"&namespace=characters&search={character_name}&include_forks=true"
                "&nsfw=false&nsfw_only=false&nsfl=false&asc=false&min_ai_rating=0"
                "&min_tokens=100&max_tokens=100000&chub=true&exclude_mine=true"
                "&sort=default&topics=&inclusive_or=false&recommended_verified=false"
                "&venus=true&count=false"
            )

        data = await self._get_json(url)
        if data is not None:
            self._search_cache.set(cache_key, data)
        return data

    async def get_character_information(self, full_path: str):
        cached = self._info_cache.get(full_path)
        if cached is not None:
            return cached

        url = f"https://gateway.chub.ai/api/characters/{full_path}?full=true&nocache=0.6411485396222347"
        data = await self._get_json(url)

        if not data:
            return self._default_character_data()

        node = data.get("node")
        if not node:
            return self._default_character_data()

        definition = node.get("definition", {})
        result = (
            node.get("name", "Unknown"),
            node.get("tagline", "No tagline"),
            node.get("avatar_url", "No avatar"),
            node.get("starCount", 0),
            node.get("n_favorites", 0),
            node.get("nTokens", 0),
            definition.get("personality", ""),
            definition.get("first_message", ""),
            definition.get("tavern_personality", ""),
            definition.get("example_dialogs", ""),
            definition.get("scenario", ""),
            definition.get("alternate_greetings", []),
        )
        self._info_cache.set(full_path, result)
        return result

    async def get_many_character_information(self, full_paths: list[str]):
        return await asyncio.gather(
            *(self.get_character_information(fp) for fp in full_paths)
        )

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


class SoulGateway:
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
